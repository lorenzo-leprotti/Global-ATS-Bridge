import { useState } from "react";
import { Download, Check, Clock, Shield, FileText, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { ProcessingSession, OutputFormat } from "@shared/schema";

interface DownloadSectionProps {
  session: ProcessingSession;
  outputFormat: OutputFormat;
  onProcessAnother: () => void;
}

export default function DownloadSection({ 
  session, 
  outputFormat,
  onProcessAnother 
}: DownloadSectionProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const formatTime = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZoneName: "short"
    });
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    
    try {
      const response = await fetch(`/api/download/${session.id}?format=${outputFormat}`);
      
      if (!response.ok) {
        throw new Error("Download failed");
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `optimized_resume.${outputFormat}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      setDownloaded(true);
    } catch (error) {
      console.error("Download error:", error);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="container-download">
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
        <Button
          onClick={handleDownload}
          disabled={isDownloading}
          className="px-8 py-6 text-sm font-bold uppercase tracking-widest bg-foreground text-background hover:bg-foreground/90 rounded-sm"
          data-testid="button-download"
        >
          {isDownloading ? (
            <>
              <Download className="w-5 h-5 mr-2 animate-pulse" />
              Downloading...
            </>
          ) : downloaded ? (
            <>
              <Check className="w-5 h-5 mr-2" />
              Downloaded
            </>
          ) : (
            <>
              <Download className="w-5 h-5 mr-2" />
              Download Optimized Resume
            </>
          )}
        </Button>
        
        <Button
          variant="outline"
          onClick={onProcessAnother}
          className="border-2 border-foreground px-6 py-6 rounded-sm"
          data-testid="button-process-another"
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          Process Another
        </Button>
      </div>

      <Card className="border-2 border-foreground/10 bg-muted/20">
        <CardContent className="p-6">
          <div className="flex items-start gap-3 mb-4">
            <Shield className="w-5 h-5 text-green-600 flex-shrink-0" />
            <h3 className="font-serif font-bold">Privacy Audit</h3>
          </div>
          
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-3">
              <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
              <span>
                Uploaded: <span className="font-mono text-muted-foreground">{formatTime(session.uploadedAt)}</span>
              </span>
            </div>
            {session.processedAt && (
              <div className="flex items-center gap-3">
                <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
                <span>
                  Processed: <span className="font-mono text-muted-foreground">{formatTime(session.processedAt)} (in memory)</span>
                </span>
              </div>
            )}
            <div className="flex items-center gap-3">
              <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
              <span>Deleted: Automatically on download</span>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <span>
                Session expires: <span className="font-mono text-muted-foreground">15 minutes</span>
              </span>
            </div>
            <div className="flex items-center gap-3 pt-2 border-t">
              <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <span className="font-mono text-xs text-muted-foreground">
                Session: {session.id.slice(0, 8)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="text-center text-sm text-muted-foreground space-y-1">
        <p className="flex items-center justify-center gap-2">
          <Check className="w-4 h-4 text-green-600" />
          Optimized for Workday, Taleo, Greenhouse
        </p>
        <p className="flex items-center justify-center gap-2">
          <Check className="w-4 h-4 text-green-600" />
          File processed in memory (Session: {session.id.slice(0, 8)})
        </p>
        <p className="flex items-center justify-center gap-2">
          <Check className="w-4 h-4 text-green-600" />
          No data retained after download
        </p>
      </div>
    </div>
  );
}
