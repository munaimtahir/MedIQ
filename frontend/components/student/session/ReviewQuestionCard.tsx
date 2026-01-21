/**
 * Review question card showing question, answer, and explanation
 */

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { Check, X, Flag, Bookmark, RefreshCw } from "lucide-react";
import { notify } from "@/lib/notify";
import { createBookmark, deleteBookmark, checkBookmark } from "@/lib/api/bookmarksApi";
import type { ReviewItem } from "@/lib/types/session";

interface ReviewQuestionCardProps {
  item: ReviewItem;
  showExplanation?: boolean;
}

const optionLabels = ["A", "B", "C", "D", "E"];

export function ReviewQuestionCard({ item, showExplanation = true }: ReviewQuestionCardProps) {
  const { question, answer } = item;
  const options = [
    question.option_a,
    question.option_b,
    question.option_c,
    question.option_d,
    question.option_e,
  ];

  const userAnswered = answer.selected_index !== null;
  const isCorrect = answer.is_correct === true;

  // Bookmark state
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [bookmarkId, setBookmarkId] = useState<string | null>(null);
  const [bookmarking, setBookmarking] = useState(false);

  // Check bookmark status on mount
  useEffect(() => {
    checkBookmarkStatus();
  }, [question.question_id]);

  async function checkBookmarkStatus() {
    try {
      const result = await checkBookmark(question.question_id);
      setIsBookmarked(result.is_bookmarked);
      setBookmarkId(result.bookmark_id);
    } catch (err) {
      console.error("Failed to check bookmark:", err);
    }
  }

  async function toggleBookmark() {
    setBookmarking(true);

    try {
      if (isBookmarked && bookmarkId) {
        // Remove bookmark
        await deleteBookmark(bookmarkId);
        setIsBookmarked(false);
        setBookmarkId(null);
        notify.success("Bookmark removed", "Question removed from bookmarks");
      } else {
        // Add bookmark
        const newBookmark = await createBookmark({ question_id: question.question_id });
        setIsBookmarked(true);
        setBookmarkId(newBookmark.id);
        notify.success("Bookmarked", "Question added to bookmarks");
      }
    } catch (err: unknown) {
      console.error("Failed to toggle bookmark:", err);
      const error = err as { message?: string };
      notify.error("Failed to update bookmark", error.message || "Please try again");
    } finally {
      setBookmarking(false);
    }
  }

  return (
    <Card className="p-6">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <Badge variant="outline">Question {question.position}</Badge>
          {answer.marked_for_review && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Flag className="h-3 w-3" />
              Marked
            </Badge>
          )}
          {answer.changed_count > 0 && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="outline" className="flex items-center gap-1">
                    <RefreshCw className="h-3 w-3" />
                    {answer.changed_count}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <p>
                    Answer changed {answer.changed_count} time{answer.changed_count > 1 ? "s" : ""}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Bookmark Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleBookmark}
                  disabled={bookmarking}
                  className={cn(isBookmarked && "text-amber-600")}
                >
                  <Bookmark className={cn("h-4 w-4", isBookmarked && "fill-current")} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isBookmarked ? "Remove bookmark" : "Add to bookmarks"}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Correctness Badge */}
          {userAnswered && (
            <Badge
              variant={isCorrect ? "default" : "destructive"}
              className="flex items-center gap-1"
            >
              {isCorrect ? (
                <>
                  <Check className="h-3 w-3" />
                  Correct
                </>
              ) : (
                <>
                  <X className="h-3 w-3" />
                  Incorrect
                </>
              )}
            </Badge>
          )}
          {!userAnswered && <Badge variant="secondary">Not Answered</Badge>}
        </div>
      </div>

      {/* Question Stem */}
      <div className="mb-4">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <p className="whitespace-pre-wrap text-base leading-relaxed">{question.stem}</p>
        </div>
      </div>

      {/* Options */}
      <div className="mb-4 space-y-2">
        {options.map((option, index) => {
          const isUserSelected = answer.selected_index === index;
          const isCorrectOption = question.correct_index === index;

          return (
            <div
              key={index}
              className={cn(
                "rounded-lg border-2 p-3 transition-colors",
                isCorrectOption && "border-green-600 bg-green-50 dark:bg-green-950/20",
                isUserSelected && !isCorrectOption && "border-red-600 bg-red-50 dark:bg-red-950/20",
                !isCorrectOption && !isUserSelected && "border-muted",
              )}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium",
                    isCorrectOption && "border-green-600 bg-green-600 text-white",
                    isUserSelected && !isCorrectOption && "border-red-600 bg-red-600 text-white",
                    !isCorrectOption && !isUserSelected && "border-muted-foreground/30",
                  )}
                >
                  {optionLabels[index]}
                </div>
                <div className="flex-1">
                  <p className="pt-0.5 text-sm leading-relaxed">{option}</p>
                  {isCorrectOption && (
                    <div className="mt-1 flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400">
                      <Check className="h-3 w-3" />
                      Correct answer
                    </div>
                  )}
                  {isUserSelected && !isCorrectOption && (
                    <div className="mt-1 flex items-center gap-1 text-xs font-medium text-red-700 dark:text-red-400">
                      <X className="h-3 w-3" />
                      Your answer
                    </div>
                  )}
                  {isUserSelected && isCorrectOption && (
                    <div className="mt-1 flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400">
                      <Check className="h-3 w-3" />
                      Your answer (Correct)
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Explanation */}
      {showExplanation && question.explanation_md && (
        <div className="mt-4 border-t pt-4">
          <h4 className="mb-2 text-sm font-semibold">Explanation</h4>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
              {question.explanation_md}
            </p>
          </div>
        </div>
      )}

      {/* Source (if available) */}
      {(question.source_book || question.source_page) && (
        <div className="mt-3 border-t pt-3">
          <p className="text-xs text-muted-foreground">
            Source: {question.source_book}
            {question.source_page && `, page ${question.source_page}`}
          </p>
        </div>
      )}
    </Card>
  );
}
