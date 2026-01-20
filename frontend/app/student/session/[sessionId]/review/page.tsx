"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft } from "lucide-react";
import { notify } from "@/lib/notify";
import { getSessionReview } from "@/lib/api/sessionsApi";
import type { SessionReview, ReviewItem } from "@/lib/types/session";
import { ReviewSummary } from "@/components/student/session/ReviewSummary";
import { ReviewQuestionCard } from "@/components/student/session/ReviewQuestionCard";
import { InlineAlert } from "@/components/auth/InlineAlert";

type ReviewFilter = "all" | "correct" | "incorrect" | "unanswered" | "marked";

export default function SessionReviewPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<SessionReview | null>(null);
  const [filter, setFilter] = useState<ReviewFilter>("all");

  useEffect(() => {
    loadReview();
  }, [sessionId]);

  async function loadReview() {
    setLoading(true);
    setError(null);

    try {
      const reviewData = await getSessionReview(sessionId);
      setReview(reviewData);
    } catch (err: any) {
      console.error("Failed to load review:", err);

      if (err?.status === 404) {
        setError("Session not found");
      } else if (err?.status === 403) {
        setError("You don't have permission to access this session");
      } else if (err?.status === 400) {
        setError("This session hasn't been submitted yet");
      } else {
        setError(err?.message || "Failed to load review");
      }
    } finally {
      setLoading(false);
    }
  }

  const filteredItems = useMemo(() => {
    if (!review) return [];

    switch (filter) {
      case "correct":
        return review.items.filter((item) => item.answer.is_correct === true);
      case "incorrect":
        return review.items.filter((item) => item.answer.is_correct === false);
      case "unanswered":
        return review.items.filter((item) => item.answer.selected_index === null);
      case "marked":
        return review.items.filter((item) => item.answer.marked_for_review);
      default:
        return review.items;
    }
  }, [review, filter]);

  const filterCounts = useMemo(() => {
    if (!review) return { all: 0, correct: 0, incorrect: 0, unanswered: 0, marked: 0 };

    return {
      all: review.items.length,
      correct: review.items.filter((item) => item.answer.is_correct === true).length,
      incorrect: review.items.filter((item) => item.answer.is_correct === false).length,
      unanswered: review.items.filter((item) => item.answer.selected_index === null).length,
      marked: review.items.filter((item) => item.answer.marked_for_review).length,
    };
  }, [review]);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-6 max-w-5xl space-y-6">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <InlineAlert variant="error" message={error || "Review not found"} />
        <Button onClick={() => router.push("/student/dashboard")} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/student/dashboard")}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Session Review</h1>
          <p className="text-muted-foreground">
            Review your answers and learn from explanations
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="mb-6">
        <ReviewSummary session={review.session} />
      </div>

      {/* Filters */}
      <div className="mb-6">
        <Tabs value={filter} onValueChange={(v) => setFilter(v as ReviewFilter)}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="all">
              All ({filterCounts.all})
            </TabsTrigger>
            <TabsTrigger value="correct">
              Correct ({filterCounts.correct})
            </TabsTrigger>
            <TabsTrigger value="incorrect">
              Incorrect ({filterCounts.incorrect})
            </TabsTrigger>
            <TabsTrigger value="unanswered">
              Unanswered ({filterCounts.unanswered})
            </TabsTrigger>
            <TabsTrigger value="marked">
              Marked ({filterCounts.marked})
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Questions */}
      {filteredItems.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>No questions match the selected filter</p>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredItems.map((item) => (
            <ReviewQuestionCard key={item.question.question_id} item={item} />
          ))}
        </div>
      )}

      {/* Back to Dashboard */}
      <div className="mt-8 flex justify-center">
        <Button onClick={() => router.push("/student/dashboard")} variant="outline">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>
    </div>
  );
}
