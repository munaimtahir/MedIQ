/**
 * Question navigator grid showing all questions
 */

import { memo, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Check, Flag } from "lucide-react";
import type { SessionQuestionSummary } from "@/lib/types/session";

interface QuestionNavigatorProps {
  questions: SessionQuestionSummary[];
  currentPosition: number;
  onNavigate: (position: number) => void;
}

export const QuestionNavigator = memo(function QuestionNavigator({
  questions,
  currentPosition,
  onNavigate,
}: QuestionNavigatorProps) {
  // Memoize processed questions to prevent unnecessary calculations
  const processedQuestions = useMemo(() => {
    return questions.map((q) => ({
      ...q,
      isCurrent: q.position === currentPosition,
      hasAnswer: q.has_answer,
      isMarked: q.marked_for_review,
    }));
  }, [questions, currentPosition]);
  
  return (
    <div className="space-y-4">
      <div>
        <h3 className="mb-2 font-semibold">Questions</h3>
        <p className="text-sm text-muted-foreground">Click to jump to any question</p>
      </div>

      <div className="grid grid-cols-5 gap-2">
        {processedQuestions.map((q) => {

          return (
            <Button
              key={q.position}
              variant={q.isCurrent ? "default" : q.hasAnswer ? "secondary" : "outline"}
              size="sm"
              onClick={() => onNavigate(q.position)}
              className={cn("relative h-10 w-full", q.isCurrent && "ring-2 ring-offset-2")}
            >
              <span>{q.position}</span>
              {q.hasAnswer && !q.isCurrent && (
                <Check className="absolute right-0.5 top-0.5 h-3 w-3 text-green-600" />
              )}
              {q.isMarked && (
                <Flag className="absolute bottom-0.5 right-0.5 h-3 w-3 text-amber-500" />
              )}
            </Button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="space-y-1 border-t pt-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded bg-primary" />
          <span>Current</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded bg-secondary" />
          <span>Answered</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded border" />
          <span>Not answered</span>
        </div>
        <div className="flex items-center gap-2">
          <Flag className="h-3 w-3 text-amber-500" />
          <span>Marked for review</span>
        </div>
      </div>
    </div>
  );
});
