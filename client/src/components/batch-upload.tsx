import { useState, useCallback, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Upload, FileText, Check, X, Download, Loader2, ArrowLeft } from "lucide-react";
import WorkAuthDropdown from "./work-auth-dropdown";
import OutputFormatSelector from "./output-format-selector";
import type { WorkAuthorization, OutputFormat, BatchProcessingResult, BatchResumeItem } from "@shared/schema";

interface BatchUploadProps {
  onBack: () => void;
}

export default function BatchUpload({ onBack }: BatchUploadProps) {
  const { toast } = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [workAuth, setWorkAuth] = useState<WorkAuthorization>("F-1 OPT (Optional Practical Training)");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("pdf");
  const [batchId, setBatchId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const { data: batchStatus, refetch: refetchStatus } = useQuery<BatchProcessingResult>({
    queryKey: ['/api/batch-status', batchId],
    enabled: !!batchId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      const allDone = data.items.every(i => i.status === "completed" || i.status === "error");
      return allDone ? false : 2000;
    }
  });

  const processMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData();
      files.forEach(file => formData.append("resumes", file));
      formData.append("workAuthorization", workAuth);
      formData.append("outputFormat", outputFormat);

      const response = await fetch("/api/batch-process", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to process batch");
      }

      return response.json() as Promise<BatchProcessingResult>;
    },
    onSuccess: (data) => {
      setBatchId(data.batchId);
      toast({
        title: "Batch Processing Started",
        description: `Processing ${data.totalFiles} resume(s)...`
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      });
    }
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      f => f.type === "application/pdf"
    );

    if (droppedFiles.length === 0) {
      toast({
        title: "Invalid Files",
        description: "Only PDF files are accepted",
        variant: "destructive"
      });
      return;
    }

    const newFiles = [...files, ...droppedFiles].slice(0, 10);
    setFiles(newFiles);
  }, [files, toast]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []).filter(
      f => f.type === "application/pdf"
    );
    const newFiles = [...files, ...selectedFiles].slice(0, 10);
    setFiles(newFiles);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleProcess = () => {
    if (files.length === 0) {
      toast({
        title: "No Files",
        description: "Please add at least one PDF resume",
        variant: "destructive"
      });
      return;
    }
    processMutation.mutate();
  };

  const handleDownload = async (sessionId: string, filename: string) => {
    try {
      const response = await fetch(`/api/download/${sessionId}?format=${outputFormat}`);
      if (!response.ok) throw new Error("Download failed");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename.replace(".pdf", `_optimized.${outputFormat}`);
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      toast({
        title: "Download Failed",
        description: "Could not download the file",
        variant: "destructive"
      });
    }
  };

  const handleReset = () => {
    setFiles([]);
    setBatchId(null);
  };

  const getStatusIcon = (status: BatchResumeItem["status"]) => {
    switch (status) {
      case "pending":
        return <div className="w-4 h-4 rounded-full border-2 border-muted-foreground" />;
      case "processing":
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case "completed":
        return <Check className="w-4 h-4 text-green-500" />;
      case "error":
        return <X className="w-4 h-4 text-red-500" />;
    }
  };

  const allComplete = batchStatus?.items.every(i => i.status === "completed" || i.status === "error");
  const progress = batchStatus 
    ? ((batchStatus.completedFiles + batchStatus.failedFiles) / batchStatus.totalFiles) * 100 
    : 0;

  return (
    <div className="w-full max-w-3xl space-y-6">
      <Button
        variant="ghost"
        onClick={onBack}
        className="gap-2"
        data-testid="button-back-single"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Single Upload
      </Button>

      <div className="text-center space-y-2">
        <h2 className="font-serif text-2xl font-bold" data-testid="text-batch-title">
          Batch Processing
        </h2>
        <p className="text-muted-foreground">
          Upload up to 10 resumes at once
        </p>
      </div>

      {!batchId ? (
        <>
          <Card>
            <CardContent className="p-6">
              <div
                className={`border-2 border-dashed rounded-md p-8 text-center transition-colors ${
                  isDragging ? "border-foreground bg-muted/50" : "border-muted-foreground/30"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                data-testid="dropzone-batch"
              >
                <Upload className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-lg mb-2">
                  Drag and drop PDF resumes here
                </p>
                <p className="text-sm text-muted-foreground mb-4">
                  or click to browse (max 10 files)
                </p>
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  multiple
                  onChange={handleFileInput}
                  className="hidden"
                  id="batch-file-input"
                  data-testid="input-batch-files"
                />
                <Button
                  variant="outline"
                  onClick={() => document.getElementById("batch-file-input")?.click()}
                  data-testid="button-browse-files"
                >
                  Browse Files
                </Button>
              </div>

              {files.length > 0 && (
                <div className="mt-6 space-y-2">
                  <p className="text-sm font-medium">
                    Selected Files ({files.length}/10)
                  </p>
                  {files.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between gap-4 p-3 bg-muted/50 rounded-md"
                      data-testid={`file-item-${index}`}
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <FileText className="w-5 h-5 text-muted-foreground shrink-0" />
                        <span className="truncate">{file.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeFile(index)}
                        data-testid={`button-remove-${index}`}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <WorkAuthDropdown value={workAuth} onChange={setWorkAuth} />
            <OutputFormatSelector value={outputFormat} onChange={setOutputFormat} />
          </div>

          <div className="flex justify-center pt-4">
            <Button
              onClick={handleProcess}
              disabled={files.length === 0 || processMutation.isPending}
              className="px-12 py-6 text-sm font-bold uppercase tracking-widest bg-foreground text-background hover:bg-foreground/90 rounded-sm"
              data-testid="button-process-batch"
            >
              {processMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                `Process ${files.length} Resume${files.length !== 1 ? "s" : ""}`
              )}
            </Button>
          </div>
        </>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-4">
              <span>Processing Status</span>
              {batchStatus && (
                <Badge variant={allComplete ? "default" : "secondary"}>
                  {batchStatus.completedFiles + batchStatus.failedFiles} / {batchStatus.totalFiles}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {batchStatus && (
              <>
                <Progress value={progress} className="h-2" />

                <div className="space-y-2">
                  {batchStatus.items.map((item, index) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between gap-4 p-3 bg-muted/50 rounded-md"
                      data-testid={`batch-item-${index}`}
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        {getStatusIcon(item.status)}
                        <span className="truncate">{item.filename}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.status === "error" && (
                          <span className="text-sm text-red-500">{item.error}</span>
                        )}
                        {item.status === "completed" && item.result?.session && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDownload(item.result!.session.id, item.filename)}
                            data-testid={`button-download-${index}`}
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {allComplete && (
                  <div className="flex flex-col items-center gap-4 pt-4">
                    <p className="text-center text-muted-foreground">
                      {batchStatus.completedFiles} of {batchStatus.totalFiles} resumes processed successfully
                      {batchStatus.failedFiles > 0 && ` (${batchStatus.failedFiles} failed)`}
                    </p>
                    <Button
                      variant="outline"
                      onClick={handleReset}
                      data-testid="button-process-more"
                    >
                      Process More Resumes
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
