import { useState } from "react";
import { AlertTriangle, Check, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { DetectedIssue, AppliedChange, ParsedResume } from "@shared/schema";

interface ComparisonViewProps {
  detectedIssues: DetectedIssue[];
  appliedChanges: AppliedChange[];
  parsedResume?: ParsedResume;
}

export default function ComparisonView({ 
  detectedIssues, 
  appliedChanges,
  parsedResume
}: ComparisonViewProps) {
  const [showJson, setShowJson] = useState(false);

  return (
    <div className="space-y-6" data-testid="container-comparison">
      <div className="text-center">
        <h2 
          className="font-serif text-2xl font-bold"
          data-testid="text-results-title"
        >
          Resume Optimized Successfully
        </h2>
        <p className="text-muted-foreground mt-2">
          Your resume has been formatted for US ATS systems
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-2 border-foreground/10">
          <CardHeader className="pb-3 flex flex-row items-center justify-between gap-2">
            <CardTitle className="font-serif text-lg uppercase tracking-wide">
              Original
            </CardTitle>
            <span className="text-sm text-muted-foreground font-mono">
              {detectedIssues.length} issues
            </span>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-80">
              <div className="space-y-3 pr-4">
                {detectedIssues.length === 0 ? (
                  <p className="text-muted-foreground text-sm italic">
                    No major issues detected
                  </p>
                ) : (
                  detectedIssues.map((issue, index) => (
                    <div 
                      key={index}
                      className="flex items-start gap-3 p-3 bg-amber-500/5 border-l-4 border-amber-500 rounded-r-sm"
                      data-testid={`issue-${index}`}
                    >
                      <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-sm">{issue.description}</p>
                        {issue.original && (
                          <p className="text-xs text-muted-foreground mt-1 font-mono">
                            {issue.original}
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="border-2 border-foreground/10">
          <CardHeader className="pb-3 flex flex-row items-center justify-between gap-2">
            <CardTitle className="font-serif text-lg uppercase tracking-wide">
              Optimized
            </CardTitle>
            <span className="text-sm text-green-600 font-mono">
              {appliedChanges.length} changes
            </span>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-80">
              <div className="space-y-3 pr-4">
                {appliedChanges.length === 0 ? (
                  <p className="text-muted-foreground text-sm italic">
                    No changes applied
                  </p>
                ) : (
                  appliedChanges.map((change, index) => (
                    <div 
                      key={index}
                      className="flex items-start gap-3 p-3 bg-green-500/5 border-l-4 border-green-500 rounded-r-sm"
                      data-testid={`change-${index}`}
                    >
                      <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-sm">{change.description}</p>
                        {change.before && change.after && (
                          <div className="mt-2 text-xs font-mono">
                            <p className="text-muted-foreground line-through">{change.before}</p>
                            <p className="text-green-700">{change.after}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {parsedResume && (
        <div className="pt-2">
          <Button
            variant="ghost"
            onClick={() => setShowJson(!showJson)}
            className="text-muted-foreground text-sm"
            data-testid="button-toggle-json"
          >
            {showJson ? (
              <>
                <ChevronUp className="w-4 h-4 mr-2" />
                Hide AI Interpretation (JSON)
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-2" />
                Show AI Interpretation (JSON)
              </>
            )}
          </Button>
          
          {showJson && (
            <div className="mt-4 p-4 bg-muted/30 rounded-sm overflow-auto max-h-96">
              <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap">
                {JSON.stringify(parsedResume, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
