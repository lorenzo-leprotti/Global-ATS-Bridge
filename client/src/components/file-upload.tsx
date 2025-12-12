import { useCallback, useState } from "react";
import { FileText, Upload, X, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

interface FileUploadProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export default function FileUpload({ selectedFile, onFileSelect }: FileUploadProps) {
  const { toast } = useToast();
  const [isDragging, setIsDragging] = useState(false);

  const validateFile = useCallback((file: File): boolean => {
    if (file.type !== "application/pdf") {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF file only",
        variant: "destructive"
      });
      return false;
    }
    
    if (file.size > MAX_FILE_SIZE) {
      toast({
        title: "File too large",
        description: "Maximum file size is 10MB",
        variant: "destructive"
      });
      return false;
    }
    
    return true;
  }, [toast]);

  const handleFile = useCallback((file: File) => {
    if (validateFile(file)) {
      onFileSelect(file);
    }
  }, [validateFile, onFileSelect]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (selectedFile) {
    return (
      <div 
        className="border-2 border-foreground rounded-sm p-6"
        data-testid="container-file-selected"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-muted flex items-center justify-center rounded-sm">
              <FileText className="w-6 h-6 text-foreground" />
            </div>
            <div>
              <p 
                className="font-medium text-foreground truncate max-w-xs"
                data-testid="text-filename"
              >
                {selectedFile.name}
              </p>
              <p 
                className="text-sm text-muted-foreground font-mono"
                data-testid="text-filesize"
              >
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onFileSelect(null)}
              className="text-muted-foreground"
              data-testid="button-remove-file"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`
        relative border-2 border-dashed rounded-sm p-10 transition-all cursor-pointer
        ${isDragging 
          ? "border-foreground bg-muted/30" 
          : "border-foreground/50 hover:border-foreground hover:bg-muted/10"
        }
      `}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      data-testid="dropzone-upload"
    >
      <input
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleInputChange}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        data-testid="input-file"
      />
      
      <div className="flex flex-col items-center gap-4 text-center pointer-events-none">
        <div className="w-16 h-16 bg-muted rounded-sm flex items-center justify-center">
          <Upload className="w-8 h-8 text-foreground" />
        </div>
        
        <div className="space-y-2">
          <p className="font-serif text-lg font-medium">
            Upload Resume (PDF only)
          </p>
          <p className="text-sm text-muted-foreground font-mono">
            PDF only • Max 10MB
          </p>
        </div>
        
        <p className="text-sm text-muted-foreground">
          Drag and drop or click to browse
        </p>
      </div>
    </div>
  );
}
