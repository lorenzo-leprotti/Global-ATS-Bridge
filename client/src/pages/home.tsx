import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import Header from "@/components/header";
import PrivacyBadge from "@/components/privacy-badge";
import FileUpload from "@/components/file-upload";
import WorkAuthDropdown from "@/components/work-auth-dropdown";
import OutputFormatSelector from "@/components/output-format-selector";
import ProcessingView from "@/components/processing-view";
import ComparisonView from "@/components/comparison-view";
import DownloadSection from "@/components/download-section";
import { Button } from "@/components/ui/button";
import type { 
  WorkAuthorization, 
  OutputFormat, 
  ResumeProcessingResult,
  ProcessingStep
} from "@shared/schema";

type ViewState = "upload" | "processing" | "results" | "error";

const initialSteps: ProcessingStep[] = [
  { id: "extract", label: "Text extraction complete", status: "pending" },
  { id: "analyze", label: "Education credentials analyzed", status: "pending" },
  { id: "convert", label: "Grade conversion applied", status: "pending" },
  { id: "auth", label: "Work authorization signal added", status: "pending" },
  { id: "layout", label: "Layout optimized for ATS", status: "pending" },
  { id: "generate", label: "Generating final document...", status: "pending" }
];

export default function Home() {
  const { toast } = useToast();
  const [view, setView] = useState<ViewState>("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [workAuth, setWorkAuth] = useState<WorkAuthorization>("F-1 OPT (Optional Practical Training)");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("pdf");
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>(initialSteps);
  const [result, setResult] = useState<ResumeProcessingResult | null>(null);

  const updateStep = useCallback((stepId: string, status: ProcessingStep["status"]) => {
    setProcessingSteps(prev => 
      prev.map(step => 
        step.id === stepId ? { ...step, status } : step
      )
    );
  }, []);

  const simulateProcessing = useCallback(async () => {
    const stepIds = ["extract", "analyze", "convert", "auth", "layout", "generate"];
    for (const stepId of stepIds) {
      updateStep(stepId, "processing");
      await new Promise(resolve => setTimeout(resolve, 800));
      updateStep(stepId, "completed");
    }
  }, [updateStep]);

  const processMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("No file selected");
      
      const formData = new FormData();
      formData.append("resume", selectedFile);
      formData.append("workAuthorization", workAuth);
      formData.append("outputFormat", outputFormat);

      const response = await fetch("/api/process-resume", {
        method: "POST",
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to process resume");
      }
      
      return response.json() as Promise<ResumeProcessingResult>;
    },
    onMutate: () => {
      setView("processing");
      setProcessingSteps(initialSteps);
      simulateProcessing();
    },
    onSuccess: (data) => {
      setResult(data);
      if (data.success) {
        setView("results");
      } else {
        setView("error");
        toast({
          title: "Processing Error",
          description: data.error || "Failed to process resume",
          variant: "destructive"
        });
      }
    },
    onError: (error: Error) => {
      setView("error");
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      });
    }
  });

  const handleOptimize = () => {
    if (!selectedFile) {
      toast({
        title: "No file selected",
        description: "Please upload a PDF resume first",
        variant: "destructive"
      });
      return;
    }
    processMutation.mutate();
  };

  const handleReset = () => {
    setView("upload");
    setSelectedFile(null);
    setResult(null);
    setProcessingSteps(initialSteps);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      
      <main className="flex-1 flex flex-col items-center px-4 py-12">
        {view === "upload" && (
          <div className="w-full max-w-2xl space-y-10">
            <div className="text-center space-y-4">
              <h1 
                className="font-serif text-3xl md:text-4xl font-bold tracking-wider uppercase"
                data-testid="text-app-title"
              >
                ULISSE
              </h1>
              <p 
                className="text-lg text-muted-foreground font-serif"
                data-testid="text-app-subtitle"
              >
                Transform International Resumes for US Jobs
              </p>
              
              <div className="flex justify-center pt-2">
                <PrivacyBadge />
              </div>
            </div>

            <FileUpload 
              selectedFile={selectedFile}
              onFileSelect={setSelectedFile}
            />

            <div className="space-y-6">
              <WorkAuthDropdown 
                value={workAuth}
                onChange={setWorkAuth}
              />

              <OutputFormatSelector 
                value={outputFormat}
                onChange={setOutputFormat}
              />
            </div>

            <div className="flex justify-center pt-4">
              <Button
                onClick={handleOptimize}
                disabled={!selectedFile || processMutation.isPending}
                className="px-12 py-6 text-sm font-bold uppercase tracking-widest bg-foreground text-background hover:bg-foreground/90 rounded-sm"
                data-testid="button-optimize"
              >
                Optimize Resume
              </Button>
            </div>
          </div>
        )}

        {view === "processing" && (
          <ProcessingView steps={processingSteps} />
        )}

        {view === "results" && result && (
          <div className="w-full max-w-5xl space-y-8">
            <ComparisonView 
              detectedIssues={result.detectedIssues || []}
              appliedChanges={result.appliedChanges || []}
              parsedResume={result.parsedResume}
            />
            
            <DownloadSection 
              session={result.session}
              outputFormat={outputFormat}
              onProcessAnother={handleReset}
            />
          </div>
        )}

        {view === "error" && (
          <div className="w-full max-w-lg text-center space-y-6">
            <div className="p-6 border-l-4 border-destructive bg-destructive/5 rounded-r-md">
              <h2 className="font-serif text-xl font-bold mb-2" data-testid="text-error-title">
                Unable to Process
              </h2>
              <p className="text-muted-foreground" data-testid="text-error-message">
                {result?.error || "An error occurred while processing your resume. Please try again with a different file."}
              </p>
              {result?.extractionPercentage !== undefined && result.extractionPercentage < 100 && (
                <p className="mt-2 text-sm text-muted-foreground">
                  Text extraction: {result.extractionPercentage}% complete
                </p>
              )}
            </div>
            
            <Button
              onClick={handleReset}
              variant="outline"
              className="border-2 border-foreground"
              data-testid="button-upload-different"
            >
              Upload Different File
            </Button>
          </div>
        )}
      </main>

      <footer className="border-t py-6 text-center text-sm text-muted-foreground font-serif">
        <p data-testid="text-footer">
          Optimized for Workday, Taleo, Greenhouse
        </p>
      </footer>
    </div>
  );
}
