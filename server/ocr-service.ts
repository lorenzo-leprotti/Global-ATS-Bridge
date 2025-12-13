import Tesseract from "tesseract.js";
import { pdfToPng } from "pdf-to-png-converter";

export interface OCRResult {
  text: string;
  confidence: number;
  wasOCRApplied: boolean;
}

export async function performOCR(imageOrPdfBuffer: Buffer): Promise<OCRResult> {
  const isPDF = imageOrPdfBuffer.slice(0, 5).toString() === '%PDF-';
  
  if (isPDF) {
    console.log("OCR: PDF buffer detected - converting pages to images first");
    return performOCROnPDF(imageOrPdfBuffer);
  }
  
  let worker: Tesseract.Worker | null = null;
  
  try {
    worker = await Tesseract.createWorker('eng');
    
    const { data } = await worker.recognize(imageOrPdfBuffer);
    
    await worker.terminate();
    worker = null;
    
    return {
      text: data.text,
      confidence: data.confidence,
      wasOCRApplied: true
    };
  } catch (error: any) {
    console.error("OCR error:", error.message);
    if (worker) {
      try {
        await worker.terminate();
      } catch (e) {
        // Ignore termination errors
      }
    }
    return {
      text: "",
      confidence: 0,
      wasOCRApplied: false
    };
  }
}

async function performOCROnPDF(pdfBuffer: Buffer): Promise<OCRResult> {
  let worker: Tesseract.Worker | null = null;
  
  try {
    console.log("OCR: Converting PDF pages to PNG images...");
    
    const pngPages = await pdfToPng(pdfBuffer, {
      viewportScale: 2.0,
      disableFontFace: true,
      useSystemFonts: false,
      verbosityLevel: 0
    });
    
    console.log(`OCR: Converted ${pngPages.length} page(s) to images`);
    
    if (pngPages.length === 0) {
      console.log("OCR: No pages converted from PDF");
      return { text: "", confidence: 0, wasOCRApplied: false };
    }
    
    worker = await Tesseract.createWorker('eng');
    
    const results: string[] = [];
    let totalConfidence = 0;
    let successCount = 0;
    
    for (let i = 0; i < pngPages.length; i++) {
      const page = pngPages[i];
      if (!page.content) {
        console.warn(`OCR: Page ${i + 1} has no content, skipping`);
        continue;
      }
      try {
        console.log(`OCR: Processing page ${i + 1}/${pngPages.length}...`);
        const { data } = await worker.recognize(page.content);
        if (data.text.trim()) {
          results.push(data.text);
          totalConfidence += data.confidence;
          successCount++;
        }
      } catch (e: any) {
        console.warn(`OCR: Failed for page ${i + 1}:`, e.message);
      }
    }
    
    await worker.terminate();
    worker = null;
    
    if (successCount === 0) {
      console.log("OCR: No text extracted from any page");
      return { text: "", confidence: 0, wasOCRApplied: false };
    }
    
    const combinedText = results.join("\n\n");
    const avgConfidence = totalConfidence / successCount;
    
    console.log(`OCR: Extracted ${combinedText.length} characters with ${avgConfidence.toFixed(1)}% avg confidence`);
    
    return {
      text: combinedText,
      confidence: avgConfidence,
      wasOCRApplied: true
    };
  } catch (error: any) {
    console.error("OCR PDF error:", error.message);
    if (worker) {
      try {
        await worker.terminate();
      } catch (e) {
        // Ignore termination errors
      }
    }
    return {
      text: "",
      confidence: 0,
      wasOCRApplied: false
    };
  }
}

export async function performOCROnMultipleImages(
  imageBuffers: Buffer[]
): Promise<OCRResult> {
  if (imageBuffers.length === 0) {
    return { text: "", confidence: 0, wasOCRApplied: false };
  }
  
  let worker: Tesseract.Worker | null = null;
  
  try {
    worker = await Tesseract.createWorker('eng');
    
    const results: string[] = [];
    let totalConfidence = 0;
    let successCount = 0;
    
    for (const buffer of imageBuffers) {
      try {
        const { data } = await worker.recognize(buffer);
        results.push(data.text);
        totalConfidence += data.confidence;
        successCount++;
      } catch (e) {
        console.warn("OCR failed for one image, continuing...");
      }
    }
    
    await worker.terminate();
    worker = null;
    
    if (successCount === 0) {
      return { text: "", confidence: 0, wasOCRApplied: false };
    }
    
    return {
      text: results.join("\n\n"),
      confidence: totalConfidence / successCount,
      wasOCRApplied: true
    };
  } catch (error: any) {
    console.error("OCR error:", error.message);
    if (worker) {
      try {
        await worker.terminate();
      } catch (e) {
        // Ignore termination errors
      }
    }
    return { text: "", confidence: 0, wasOCRApplied: false };
  }
}

export function isLikelyScannedPDF(text: string, pageCount: number): boolean {
  const textLength = text.trim().length;
  const charsPerPage = textLength / Math.max(pageCount, 1);
  
  return charsPerPage < 100;
}
