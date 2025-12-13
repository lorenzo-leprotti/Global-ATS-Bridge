import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import multer from "multer";
import * as pdfParse from "pdf-parse";
import { storage } from "./storage";
import { parseResumeWithAI, validateParsedResume } from "./openai-service";
import { detectAndConvertGrades, applyGradeConversionsToResume } from "./grade-conversion";
import { generatePDF, generateDOCX } from "./pdf-generator";
import { performOCR, isLikelyScannedPDF } from "./ocr-service";
import { getAllTemplates, getTemplate, type IndustryTemplate } from "./templates";
import { scoreResume } from "./resume-scoring";
import type { 
  ResumeProcessingResult, 
  DetectedIssue, 
  AppliedChange,
  WorkAuthorization,
  OutputFormat,
  BatchProcessingResult,
  BatchResumeItem
} from "@shared/schema";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024
  },
  fileFilter: (_req, file, cb) => {
    if (file.mimetype === "application/pdf") {
      cb(null, true);
    } else {
      cb(new Error("Only PDF files are allowed"));
    }
  }
});

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.get("/api/templates", async (_req: Request, res: Response) => {
    try {
      const templates = getAllTemplates();
      return res.json(templates.map(t => ({
        id: t.id,
        name: t.name,
        description: t.description
      })));
    } catch (error: any) {
      return res.status(500).json({ error: error.message });
    }
  });

  app.post("/api/process-resume", upload.single("resume"), async (req: Request, res: Response) => {
    try {
      const file = req.file;
      const workAuthorization = req.body.workAuthorization as WorkAuthorization;
      const outputFormat = req.body.outputFormat as OutputFormat;
      const templateId = (req.body.templateId as IndustryTemplate) || "general";

      console.log("[process-resume] Request received:", {
        hasFile: !!file,
        fileSize: file?.size,
        fileName: file?.originalname,
        workAuthorization: workAuthorization || "missing",
        outputFormat,
        templateId
      });

      if (!file) {
        console.log("[process-resume] ERROR: No file in request");
        return res.status(400).json({ 
          success: false, 
          error: "No file uploaded. Please select a PDF file and try again." 
        });
      }

      if (!workAuthorization) {
        console.log("[process-resume] ERROR: No work authorization");
        return res.status(400).json({ 
          success: false, 
          error: "Work authorization is required. Please select your work authorization status." 
        });
      }

      const session = storage.createSession(workAuthorization, outputFormat || "pdf");

      let extractedText = "";
      let wasOCRApplied = false;
      let ocrConfidence = 0;
      
      try {
        console.log("[process-resume] Parsing PDF...");
        const parsePdf = (pdfParse as any).default || pdfParse;
        const pdfData = await parsePdf(file.buffer);
        extractedText = pdfData.text;
        console.log(`[process-resume] PDF parsed, text length: ${extractedText.length}, pages: ${pdfData.numpages}`);
        
        const pageCount = pdfData.numpages || 1;
        if (isLikelyScannedPDF(extractedText, pageCount)) {
          console.log("[process-resume] Low text density detected, attempting OCR...");
          try {
            const ocrResult = await performOCR(file.buffer);
            if (ocrResult.text.trim().length > extractedText.trim().length) {
              extractedText = ocrResult.text;
              wasOCRApplied = true;
              ocrConfidence = ocrResult.confidence;
              console.log(`[process-resume] OCR completed with ${ocrConfidence.toFixed(1)}% confidence, text length: ${extractedText.length}`);
            }
          } catch (ocrError) {
            console.warn("[process-resume] OCR fallback failed:", ocrError);
          }
        }
      } catch (parseError: any) {
        console.log("[process-resume] PDF parsing failed:", parseError.message);
        console.log("[process-resume] Attempting OCR on raw buffer...");
        try {
          const ocrResult = await performOCR(file.buffer);
          extractedText = ocrResult.text;
          wasOCRApplied = true;
          ocrConfidence = ocrResult.confidence;
          console.log(`[process-resume] OCR completed with ${ocrConfidence.toFixed(1)}% confidence, text length: ${extractedText.length}`);
        } catch (ocrError: any) {
          console.log("[process-resume] ERROR: Both PDF parsing and OCR failed");
          return res.status(400).json({
            success: false,
            session,
            error: "Unable to extract text from PDF. The file may be corrupted or password-protected. Please try a different file.",
            extractionPercentage: 0
          } as ResumeProcessingResult);
        }
      }
      
      console.log(`[process-resume] Final extracted text length: ${extractedText?.length || 0}`);
      
      if (!extractedText || extractedText.trim().length < 50) {
        console.log("[process-resume] ERROR: Insufficient text extracted");
        return res.status(400).json({
          success: false,
          session,
          error: `Could not extract sufficient text from your resume (only ${extractedText?.trim().length || 0} characters found). Please ensure the PDF contains readable text, not just images.`,
          extractionPercentage: extractedText ? Math.min(extractedText.length / 500 * 100, 20) : 0
        } as ResumeProcessingResult);
      }

      const detectedIssues: DetectedIssue[] = [];
      const appliedChanges: AppliedChange[] = [];

      if (wasOCRApplied) {
        detectedIssues.push({
          type: "info",
          original: "Scanned/image-based PDF detected",
          description: "Document appears to be scanned or image-based"
        });
        appliedChanges.push({
          type: "enhancement",
          description: `OCR text extraction applied (${ocrConfidence.toFixed(0)}% confidence)`
        });
      }

      if (extractedText.toLowerCase().includes("photo") || 
          extractedText.includes("headshot") ||
          /\.(jpg|jpeg|png|gif)\s/i.test(extractedText)) {
        detectedIssues.push({
          type: "warning",
          original: "Photo/image reference detected",
          description: "Resume contains photo reference"
        });
        appliedChanges.push({
          type: "fix",
          description: "Photo removed from resume"
        });
      }

      const { conversions } = detectAndConvertGrades(extractedText);
      for (const conv of conversions) {
        detectedIssues.push({
          type: "info",
          original: conv.original,
          description: `International grade format detected: ${conv.original}`
        });
        appliedChanges.push({
          type: "enhancement",
          description: "Grade converted to US GPA",
          before: conv.original,
          after: conv.converted
        });
      }

      appliedChanges.push({
        type: "fix",
        description: "Single-column ATS-friendly layout applied"
      });

      appliedChanges.push({
        type: "enhancement",
        description: `Work authorization added: ${workAuthorization}`
      });

      let parsedResume;
      try {
        parsedResume = await parseResumeWithAI(extractedText, workAuthorization);
      } catch (aiError: any) {
        console.error("AI parsing error:", aiError);
        return res.status(500).json({
          success: false,
          session,
          error: "Failed to process resume with AI. Please try again.",
          originalText: extractedText.slice(0, 500)
        } as ResumeProcessingResult);
      }

      const validation = validateParsedResume(parsedResume);
      if (!validation.valid) {
        console.warn("Resume validation warnings:", validation.errors);
      }

      const finalResume = applyGradeConversionsToResume(parsedResume, conversions);

      const score = scoreResume(finalResume, templateId);

      session.processedAt = new Date().toISOString();

      storage.updateSession(session.id, {
        session,
        parsedResume: finalResume,
        originalText: extractedText,
        detectedIssues,
        appliedChanges,
        workAuthorization,
        outputFormat: outputFormat || "pdf"
      });

      const result: ResumeProcessingResult = {
        success: true,
        session,
        parsedResume: finalResume,
        detectedIssues,
        appliedChanges,
        extractionPercentage: 100,
        score
      };

      return res.json(result);
    } catch (error: any) {
      console.error("Resume processing error:", error);
      return res.status(500).json({
        success: false,
        error: error.message || "An unexpected error occurred"
      });
    }
  });

  app.get("/api/download/:sessionId", async (req: Request, res: Response) => {
    try {
      const { sessionId } = req.params;
      const format = (req.query.format as OutputFormat) || "pdf";

      const sessionData = storage.getSession(sessionId);
      
      if (!sessionData) {
        return res.status(404).json({ 
          error: "Session not found or expired" 
        });
      }

      if (!sessionData.parsedResume) {
        return res.status(400).json({ 
          error: "Resume not processed yet" 
        });
      }

      let buffer: Buffer;
      let contentType: string;
      let filename: string;

      if (format === "docx") {
        buffer = await generateDOCX(sessionData.parsedResume);
        contentType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        filename = "optimized_resume.docx";
      } else {
        buffer = await generatePDF(sessionData.parsedResume);
        contentType = "application/pdf";
        filename = "optimized_resume.pdf";
      }

      res.setHeader("Content-Type", contentType);
      res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
      res.setHeader("Content-Length", buffer.length);

      storage.deleteSession(sessionId);

      return res.send(buffer);
    } catch (error: any) {
      console.error("Download error:", error);
      return res.status(500).json({ 
        error: "Failed to generate document" 
      });
    }
  });

  app.get("/api/session/:sessionId", async (req: Request, res: Response) => {
    try {
      const { sessionId } = req.params;
      const sessionData = storage.getSession(sessionId);
      
      if (!sessionData) {
        return res.status(404).json({ 
          error: "Session not found or expired" 
        });
      }

      return res.json({
        session: sessionData.session,
        hasResume: !!sessionData.parsedResume
      });
    } catch (error: any) {
      return res.status(500).json({ 
        error: error.message 
      });
    }
  });

  app.post("/api/batch-process", upload.array("resumes", 10), async (req: Request, res: Response) => {
    try {
      const files = req.files as Express.Multer.File[];
      const workAuthorization = req.body.workAuthorization as WorkAuthorization;
      const outputFormat = (req.body.outputFormat as OutputFormat) || "pdf";

      if (!files || files.length === 0) {
        return res.status(400).json({ 
          success: false, 
          error: "No files uploaded" 
        });
      }

      if (files.length > 10) {
        return res.status(400).json({
          success: false,
          error: "Maximum 10 files allowed per batch"
        });
      }

      if (!workAuthorization) {
        return res.status(400).json({ 
          success: false, 
          error: "Work authorization is required" 
        });
      }

      const filenames = files.map(f => f.originalname);
      const batchSession = storage.createBatchSession(workAuthorization, outputFormat, filenames);

      const processFile = async (file: Express.Multer.File, itemId: string): Promise<void> => {
        storage.updateBatchItem(batchSession.batchId, itemId, { status: "processing" });

        try {
          let extractedText = "";
          let wasOCRApplied = false;
          let ocrConfidence = 0;

          try {
            const parsePdf = (pdfParse as any).default || pdfParse;
            const pdfData = await parsePdf(file.buffer);
            extractedText = pdfData.text;

            const pageCount = pdfData.numpages || 1;
            if (isLikelyScannedPDF(extractedText, pageCount)) {
              try {
                const ocrResult = await performOCR(file.buffer);
                if (ocrResult.text.trim().length > extractedText.trim().length) {
                  extractedText = ocrResult.text;
                  wasOCRApplied = true;
                  ocrConfidence = ocrResult.confidence;
                }
              } catch (ocrError) {
                console.warn(`OCR fallback failed for ${file.originalname}:`, ocrError);
              }
            }
          } catch (parseError) {
            try {
              const ocrResult = await performOCR(file.buffer);
              extractedText = ocrResult.text;
              wasOCRApplied = true;
              ocrConfidence = ocrResult.confidence;
            } catch (ocrError) {
              throw new Error("Unable to extract text from PDF");
            }
          }

          if (!extractedText || extractedText.trim().length < 50) {
            throw new Error("Insufficient text extracted from resume");
          }

          const detectedIssues: DetectedIssue[] = [];
          const appliedChanges: AppliedChange[] = [];

          if (wasOCRApplied) {
            detectedIssues.push({
              type: "info",
              original: "Scanned/image-based PDF detected",
              description: "Document appears to be scanned or image-based"
            });
            appliedChanges.push({
              type: "enhancement",
              description: `OCR text extraction applied (${ocrConfidence.toFixed(0)}% confidence)`
            });
          }

          const { conversions } = detectAndConvertGrades(extractedText);
          for (const conv of conversions) {
            detectedIssues.push({
              type: "info",
              original: conv.original,
              description: `International grade format detected: ${conv.original}`
            });
            appliedChanges.push({
              type: "enhancement",
              description: "Grade converted to US GPA",
              before: conv.original,
              after: conv.converted
            });
          }

          appliedChanges.push({
            type: "fix",
            description: "Single-column ATS-friendly layout applied"
          });

          appliedChanges.push({
            type: "enhancement",
            description: `Work authorization added: ${workAuthorization}`
          });

          const parsedResume = await parseResumeWithAI(extractedText, workAuthorization);
          const finalResume = applyGradeConversionsToResume(parsedResume, conversions);

          const session = storage.createSession(workAuthorization, outputFormat);
          session.processedAt = new Date().toISOString();

          storage.updateSession(session.id, {
            session,
            parsedResume: finalResume,
            originalText: extractedText,
            detectedIssues,
            appliedChanges,
            workAuthorization,
            outputFormat
          });

          storage.updateBatchItem(batchSession.batchId, itemId, {
            status: "completed",
            result: {
              success: true,
              session,
              parsedResume: finalResume,
              detectedIssues,
              appliedChanges,
              extractionPercentage: 100
            }
          });
        } catch (error: any) {
          storage.updateBatchItem(batchSession.batchId, itemId, {
            status: "error",
            error: error.message || "Processing failed"
          });
        }
      };

      res.json({
        batchId: batchSession.batchId,
        totalFiles: files.length,
        completedFiles: 0,
        failedFiles: 0,
        items: batchSession.items
      } as BatchProcessingResult);

      (async () => {
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          const itemId = batchSession.items[i].id;
          try {
            await processFile(file, itemId);
          } catch (err) {
            console.error(`Batch processing error for ${file.originalname}:`, err);
          }
        }
      })();
    } catch (error: any) {
      console.error("Batch processing error:", error);
      return res.status(500).json({
        success: false,
        error: error.message || "An unexpected error occurred"
      });
    }
  });

  app.get("/api/batch-status/:batchId", async (req: Request, res: Response) => {
    try {
      const { batchId } = req.params;
      const batchData = storage.getBatchSession(batchId);

      if (!batchData) {
        return res.status(404).json({
          error: "Batch session not found or expired"
        });
      }

      const completedFiles = batchData.items.filter(i => i.status === "completed").length;
      const failedFiles = batchData.items.filter(i => i.status === "error").length;

      return res.json({
        batchId: batchData.batchId,
        totalFiles: batchData.items.length,
        completedFiles,
        failedFiles,
        items: batchData.items
      } as BatchProcessingResult);
    } catch (error: any) {
      return res.status(500).json({
        error: error.message
      });
    }
  });

  app.get("/api/batch-download/:batchId", async (req: Request, res: Response) => {
    try {
      const { batchId } = req.params;
      const batchData = storage.getBatchSession(batchId);

      if (!batchData) {
        return res.status(404).json({
          error: "Batch session not found or expired"
        });
      }

      const completedItems = batchData.items.filter(i => i.status === "completed" && i.result?.session);
      
      if (completedItems.length === 0) {
        return res.status(400).json({
          error: "No completed resumes to download"
        });
      }

      const downloadLinks = completedItems.map(item => ({
        filename: item.filename,
        sessionId: item.result!.session.id,
        downloadUrl: `/api/download/${item.result!.session.id}?format=${batchData.outputFormat}`
      }));

      return res.json({
        batchId,
        format: batchData.outputFormat,
        downloads: downloadLinks
      });
    } catch (error: any) {
      return res.status(500).json({
        error: error.message
      });
    }
  });

  return httpServer;
}
