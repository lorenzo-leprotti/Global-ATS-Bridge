import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, AlertCircle, Lightbulb } from "lucide-react";
import type { ResumeScore } from "@shared/schema";

interface ScoreDisplayProps {
  score: ResumeScore;
}

function getGradeColor(grade: string): string {
  switch (grade) {
    case "A": return "bg-green-500/20 text-green-700 dark:text-green-400";
    case "B": return "bg-blue-500/20 text-blue-700 dark:text-blue-400";
    case "C": return "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400";
    case "D": return "bg-orange-500/20 text-orange-700 dark:text-orange-400";
    case "F": return "bg-red-500/20 text-red-700 dark:text-red-400";
    default: return "bg-muted text-muted-foreground";
  }
}

function getScoreColor(score: number): string {
  if (score >= 90) return "bg-green-500";
  if (score >= 80) return "bg-blue-500";
  if (score >= 70) return "bg-yellow-500";
  if (score >= 60) return "bg-orange-500";
  return "bg-red-500";
}

export default function ScoreDisplay({ score }: ScoreDisplayProps) {
  return (
    <Card className="border-2 border-foreground/10">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between gap-4">
          <span className="font-serif text-lg">Resume Score</span>
          <div className="flex items-center gap-3">
            <span 
              className="text-3xl font-bold" 
              data-testid="text-overall-score"
            >
              {score.overallScore}
            </span>
            <Badge 
              className={`text-lg px-3 py-1 ${getGradeColor(score.grade)}`}
              data-testid="badge-grade"
            >
              {score.grade}
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          {score.breakdown.map((item, index) => {
            const maxScore = item.maxScore || 1;
            const progressValue = Math.min(100, Math.max(0, (item.score / maxScore) * 100));
            return (
              <div key={index} className="space-y-1" data-testid={`score-category-${index}`}>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{item.category}</span>
                  <span className="font-medium">{item.score}/{item.maxScore}</span>
                </div>
                <Progress 
                  value={isNaN(progressValue) ? 0 : progressValue} 
                  className="h-2"
                />
              </div>
            );
          })}
        </div>

        {score.topSuggestions.length > 0 && (
          <div className="pt-4 border-t border-foreground/10">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium">Top Suggestions</span>
            </div>
            <ul className="space-y-2">
              {score.topSuggestions.map((suggestion, index) => (
                <li 
                  key={index} 
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                  data-testid={`suggestion-${index}`}
                >
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-muted-foreground/60" />
                  <span>{suggestion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {score.overallScore >= 80 && (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400 pt-2">
            <CheckCircle className="w-4 h-4" />
            <span>Your resume is well-optimized for ATS systems</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
