/**
 * Question view with stem, options, and answer selection
 */

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight, Flag, Loader2 } from "lucide-react";
import type { CurrentQuestion } from "@/lib/types/session";

interface QuestionViewProps {
  question: CurrentQuestion;
  selectedIndex: number | null;
  isMarkedForReview: boolean;
  isSaving: boolean;
  totalQuestions: number;
  onSelectOption: (index: number) => void;
  onToggleMarkForReview: (marked: boolean) => void;
  onPrevious: () => void;
  onNext: () => void;
  canGoPrevious: boolean;
  canGoNext: boolean;
}

const optionLabels = ["A", "B", "C", "D", "E"];

export function QuestionView({
  question,
  selectedIndex,
  isMarkedForReview,
  isSaving,
  totalQuestions,
  onSelectOption,
  onToggleMarkForReview,
  onPrevious,
  onNext,
  canGoPrevious,
  canGoNext,
}: QuestionViewProps) {
  const options = [
    question.option_a,
    question.option_b,
    question.option_c,
    question.option_d,
    question.option_e,
  ];

  return (
    <div className="space-y-6">
      {/* Question Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Badge variant="outline">Question {question.position}</Badge>
            <span className="text-sm text-muted-foreground">of {totalQuestions}</span>
          </div>
        </div>
        {isSaving && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Saving...</span>
          </div>
        )}
      </div>

      {/* Question Stem */}
      <Card className="p-6">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <p className="whitespace-pre-wrap text-base leading-relaxed">{question.stem}</p>
        </div>
      </Card>

      {/* Options */}
      <div className="space-y-3">
        {options.map((option, index) => (
          <Card
            key={index}
            className={cn(
              "cursor-pointer p-4 transition-colors hover:bg-accent",
              selectedIndex === index && "bg-accent ring-2 ring-primary",
            )}
            onClick={() => onSelectOption(index)}
          >
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium",
                  selectedIndex === index
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-muted-foreground/30",
                )}
              >
                {optionLabels[index]}
              </div>
              <p className="flex-1 pt-0.5 text-sm leading-relaxed">{option}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Mark for Review */}
      <div className="flex items-center space-x-2 rounded-lg border p-4">
        <Checkbox
          id="mark-review"
          checked={isMarkedForReview}
          onCheckedChange={(checked) => onToggleMarkForReview(checked === true)}
        />
        <Label htmlFor="mark-review" className="flex cursor-pointer items-center gap-2 font-normal">
          <Flag className="h-4 w-4 text-amber-500" />
          <span>Mark this question for review</span>
        </Label>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between gap-4 pt-4">
        <Button variant="outline" onClick={onPrevious} disabled={!canGoPrevious}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Previous
        </Button>
        <Button variant="outline" onClick={onNext} disabled={!canGoNext}>
          Next
          <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
