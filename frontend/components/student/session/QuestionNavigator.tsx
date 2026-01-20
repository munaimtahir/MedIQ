/**
 * Question navigator grid showing all questions
 */

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Check, Flag } from "lucide-react";
import type { SessionQuestionSummary } from "@/lib/types/session";

interface QuestionNavigatorProps {
  questions: SessionQuestionSummary[];
  currentPosition: number;
  onNavigate: (position: number) => void;
}

export function QuestionNavigator({
  questions,
  currentPosition,
  onNavigate,
}: QuestionNavigatorProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold mb-2">Questions</h3>
        <p className="text-sm text-muted-foreground">
          Click to jump to any question
        </p>
      </div>

      <div className="grid grid-cols-5 gap-2">
        {questions.map((q) => {
          const isCurrent = q.position === currentPosition;
          const hasAnswer = q.has_answer;
          const isMarked = q.marked_for_review;

          return (
            <Button
              key={q.position}
              variant={isCurrent ? "default" : hasAnswer ? "secondary" : "outline"}
              size="sm"
              onClick={() => onNavigate(q.position)}
              className={cn(
                "relative h-10 w-full",
                isCurrent && "ring-2 ring-offset-2"
              )}
            >
              <span>{q.position}</span>
              {hasAnswer && !isCurrent && (
                <Check className="absolute top-0.5 right-0.5 h-3 w-3 text-green-600" />
              )}
              {isMarked && (
                <Flag className="absolute bottom-0.5 right-0.5 h-3 w-3 text-amber-500" />
              )}
            </Button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="space-y-1 text-xs text-muted-foreground border-t pt-3">
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
}
