import { Check, Loader2, Circle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import type { ProcessingStep } from "@shared/schema";

interface ProcessingViewProps {
  steps: ProcessingStep[];
}

export default function ProcessingView({ steps }: ProcessingViewProps) {
  const completedCount = steps.filter(s => s.status === "completed").length;
  const progress = (completedCount / steps.length) * 100;

  return (
    <div 
      className="w-full max-w-lg space-y-8"
      data-testid="container-processing"
    >
      <div className="text-center space-y-2">
        <h2 className="font-serif text-2xl font-bold" data-testid="text-processing-title">
          Processing your resume...
        </h2>
        <p className="text-muted-foreground">
          This may take a moment
        </p>
      </div>

      <div className="space-y-2">
        <Progress 
          value={progress} 
          className="h-1 bg-muted"
          data-testid="progress-bar"
        />
        <p className="text-right text-sm font-mono text-muted-foreground">
          {Math.round(progress)}%
        </p>
      </div>

      <div className="space-y-4">
        {steps.map((step) => (
          <div 
            key={step.id}
            className={`flex items-center gap-3 transition-opacity ${
              step.status === "pending" ? "opacity-40" : "opacity-100"
            }`}
            data-testid={`step-${step.id}`}
          >
            {step.status === "completed" && (
              <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
            )}
            {step.status === "processing" && (
              <Loader2 className="w-5 h-5 animate-spin text-foreground flex-shrink-0" />
            )}
            {step.status === "pending" && (
              <Circle className="w-5 h-5 text-muted-foreground flex-shrink-0" />
            )}
            {step.status === "error" && (
              <div className="w-5 h-5 rounded-full bg-destructive flex items-center justify-center flex-shrink-0">
                <span className="text-destructive-foreground text-xs font-bold">!</span>
              </div>
            )}
            
            <span className={`font-serif ${
              step.status === "completed" ? "text-foreground" : "text-muted-foreground"
            }`}>
              {step.status === "completed" ? step.label.replace("...", "") : step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
