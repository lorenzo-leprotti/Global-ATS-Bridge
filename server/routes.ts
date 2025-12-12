import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import multer from "multer";
import * as pdfParse from "pdf-parse";
import { storage } from "./storage";
import { parseResumeWithAI, validateParsedResume } from "./openai-service";
import { detectAndConvertGrades } from "./grade-conversion";
import { generatePDF, generateDOCX } from "./pdf-generator";
import type { 
  ResumeProcessingResult, 
  DetectedIssue, 
  AppliedChange,
  WorkAuthorization,
  OutputFormat 
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

  app.post("/api/process-resume", upload.single("resume"), async (req: Request, res: Response) => {
    try {
      const file = req.file;
      const workAuthorization = req.body.workAuthorization as WorkAuthorization;
      const outputFormat = req.body.outputFormat as OutputFormat;

      if (!file) {
        return res.status(400).json({ 
          success: false, 
          error: "No file uploaded" 
        });
      }

      if (!workAuthorization) {
        return res.status(400).json({ 
          success: false, 
          error: "Work authorization is required" 
        });
      }

      const session = storage.createSession(workAuthorization, outputFormat || "pdf");

      let pdfData;
      try {
        const parsePdf = (pdfParse as any).default || pdfParse;
        pdfData = await parsePdf(file.buffer);
      } catch (parseError) {
        return res.status(400).json({
          success: false,
          session,
          error: "Unable to extract text from PDF. This may be a scanned or image-based PDF.",
          extractionPercentage: 0
        } as ResumeProcessingResult);
      }

      const extractedText = pdfData.text;
      
      if (!extractedText || extractedText.trim().length < 50) {
        return res.status(400).json({
          success: false,
          session,
          error: "This appears to be a scanned/image-based PDF. Please upload a text-based resume.",
          extractionPercentage: extractedText ? Math.min(extractedText.length / 500 * 100, 20) : 0
        } as ResumeProcessingResult);
      }

      const detectedIssues: DetectedIssue[] = [];
      const appliedChanges: AppliedChange[] = [];

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

      session.processedAt = new Date().toISOString();

      storage.updateSession(session.id, {
        session,
        parsedResume,
        originalText: extractedText,
        detectedIssues,
        appliedChanges,
        workAuthorization,
        outputFormat: outputFormat || "pdf"
      });

      const result: ResumeProcessingResult = {
        success: true,
        session,
        parsedResume,
        detectedIssues,
        appliedChanges,
        extractionPercentage: 100
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

  return httpServer;
}
