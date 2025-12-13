import Tesseract from "tesseract.js";

export interface OCRResult {
  text: string;
  confidence: number;
  wasOCRApplied: boolean;
}

export async function performOCR(imageBuffer: Buffer): Promise<OCRResult> {
  let worker: Tesseract.Worker | null = null;
  
  try {
    const isPDF = imageBuffer.slice(0, 5).toString() === '%PDF-';
    if (isPDF) {
      console.log("OCR: PDF buffer detected - Tesseract cannot process PDFs directly");
      return {
        text: "",
        confidence: 0,
        wasOCRApplied: false
      };
    }

    worker = await Tesseract.createWorker('eng');
    
    const { data } = await worker.recognize(imageBuffer);
    
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
