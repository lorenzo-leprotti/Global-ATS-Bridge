import Tesseract from "tesseract.js";

export interface OCRResult {
  text: string;
  confidence: number;
  wasOCRApplied: boolean;
}

export async function performOCR(imageBuffer: Buffer): Promise<OCRResult> {
  try {
    const worker = await Tesseract.createWorker('eng');
    
    const { data } = await worker.recognize(imageBuffer);
    
    await worker.terminate();
    
    return {
      text: data.text,
      confidence: data.confidence,
      wasOCRApplied: true
    };
  } catch (error: any) {
    console.error("OCR error:", error);
    throw new Error(`OCR processing failed: ${error.message}`);
  }
}

export async function performOCROnMultipleImages(
  imageBuffers: Buffer[]
): Promise<OCRResult> {
  if (imageBuffers.length === 0) {
    return { text: "", confidence: 0, wasOCRApplied: false };
  }
  
  try {
    const worker = await Tesseract.createWorker('eng');
    
    const results: string[] = [];
    let totalConfidence = 0;
    
    for (const buffer of imageBuffers) {
      const { data } = await worker.recognize(buffer);
      results.push(data.text);
      totalConfidence += data.confidence;
    }
    
    await worker.terminate();
    
    return {
      text: results.join("\n\n"),
      confidence: totalConfidence / imageBuffers.length,
      wasOCRApplied: true
    };
  } catch (error: any) {
    console.error("OCR error:", error);
    throw new Error(`OCR processing failed: ${error.message}`);
  }
}

export function isLikelyScannedPDF(text: string, pageCount: number): boolean {
  const textLength = text.trim().length;
  const charsPerPage = textLength / Math.max(pageCount, 1);
  
  return charsPerPage < 100;
}
