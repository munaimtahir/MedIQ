"use client";

/**
 * Optimized Session Player Page
 * 
 * Features:
 * - SWR for caching and automatic revalidation
 * - Prefetching next questions for instant navigation
 * - Thin API endpoints for minimal payloads
 * - Optimistic updates with error handling
 * - No refetch-on-focus for better UX
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import useSWR, { useSWRConfig } from "swr";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Menu } from "lucide-react";
import { notify } from "@/lib/notify";
import {
  getSessionStateThin,
  getSessionQuestion,
  prefetchQuestions,
  submitAnswerThin,
  submitSessionThin,
} from "@/lib/api/sessionsApi";
import type {
  SessionStateThin,
  QuestionWithAnswerState,
  AnswerSubmitThinRequest,
  SessionQuestionSummary,
} from "@/lib/types/session";
import { SessionTopBar } from "@/components/student/session/SessionTopBar";
import { QuestionNavigator } from "@/components/student/session/QuestionNavigator";
import { QuestionView } from "@/components/student/session/QuestionView";
import { SubmitConfirmDialog } from "@/components/student/session/SubmitConfirmDialog";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { useTelemetry } from "@/lib/hooks/useTelemetry";

// SWR cache keys
const getStateKey = (sessionId: string) => `/v1/sessions/${sessionId}/state`;
const getQuestionKey = (sessionId: string, index: number) =>
  `/v1/sessions/${sessionId}/question?index=${index}`;

export default function SessionPlayerPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;
  const { mutate } = useSWRConfig();

  // Telemetry
  const { track, flush } = useTelemetry(sessionId);

  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [showMobileNav, setShowMobileNav] = useState(false);
  const [savingAnswer, setSavingAnswer] = useState(false);

  // Session state query (thin, polls only if exam timer visible)
  const {
    data: sessionState,
    error: stateError,
    isLoading: stateLoading,
    mutate: mutateState,
  } = useSWR<SessionStateThin>(
    sessionId ? [getStateKey(sessionId), sessionId] : null,
    ([, sid]: [string, string]) => getSessionStateThin(sid),
    {
      refreshInterval: (data) => {
        // Only poll if exam mode and timer is active
        if (data?.mode === "EXAM" && data?.status === "ACTIVE") {
          return 15000; // 15 seconds for timer sync
        }
        return 0; // No polling for tutor mode or submitted sessions
      },
      revalidateOnFocus: false, // Disable refetch on window focus for player
      revalidateOnReconnect: true,
      dedupingInterval: 5000, // 5 seconds dedupe
      onError: (err) => {
        console.error("Failed to load session state:", err);
        if ((err as { status?: number }).status === 404) {
          notify.error("Session not found", "This session may have been deleted");
        }
      },
    },
  );

  // Current question index (1-based)
  const currentPosition = sessionState?.current_index ?? 1;

  // Current question query (cached, keepPreviousData for smooth transitions)
  const {
    data: currentQuestionData,
    error: questionError,
    isLoading: questionLoading,
    mutate: mutateQuestion,
  } = useSWR<QuestionWithAnswerState>(
    sessionId && currentPosition ? [getQuestionKey(sessionId, currentPosition), sessionId, currentPosition] : null,
    ([, sid, idx]: [string, string, number]) => getSessionQuestion(sid, idx),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 0, // No dedupe, we want fresh data on navigation
      keepPreviousData: true, // Keep previous question visible while loading next
    },
  );

  // Prefetch next questions when current index changes
  const prefetchNext = useCallback(
    async (fromIndex: number) => {
      if (!sessionState) return;

      const count = Math.min(2, sessionState.total_questions - fromIndex + 1);
      if (count <= 0) return;

      try {
        const data = await prefetchQuestions(sessionId, fromIndex, count);
        // Pre-populate SWR cache
        data.items.forEach((item) => {
          mutate(getQuestionKey(sessionId, item.index), item, false);
        });
      } catch (err) {
        // Silent fail for prefetch
        console.warn("Prefetch failed:", err);
      }
    },
    [sessionId, sessionState, mutate],
  );

  // Prefetch next questions when index changes
  useEffect(() => {
    if (currentPosition > 0 && sessionState) {
      // Prefetch i+1 and i+2
      prefetchNext(currentPosition + 1);
    }
  }, [currentPosition, sessionState, prefetchNext]);

  // Track question view when position changes
  useEffect(() => {
    if (currentQuestionData && currentPosition > 0) {
      track("QUESTION_VIEWED", { position: currentPosition }, currentQuestionData.question.question_id);
    }
  }, [currentPosition, currentQuestionData, track]);

  // Track blur/focus
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleVisibilityChange = () => {
      const state = document.visibilityState === "hidden" ? "blur" : "focus";
      track("PAUSE_BLUR", { state });
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [track]);

  // Check if session is no longer active
  useEffect(() => {
    if (sessionState && sessionState.status !== "ACTIVE") {
      router.push(`/student/session/${sessionId}/review`);
    }
  }, [sessionState, sessionId, router]);

  const handleExpire = useCallback(() => {
    notify.info("Time's up!", "Your session has expired and will be submitted automatically");
    handleSubmitConfirmed();
  }, []);

  // Handle answer submission (optimistic update)
  const handleSelectOption = useCallback(
    async (questionId: string, index: number) => {
      if (!currentQuestionData) return;

      setSavingAnswer(true);

      // Optimistic update
      const optimisticData: QuestionWithAnswerState = {
        ...currentQuestionData,
        answer_state: {
          ...currentQuestionData.answer_state,
          selected_index: index,
        },
      };
      mutateQuestion(optimisticData, false);

      try {
        const payload: AnswerSubmitThinRequest = {
          index: currentPosition,
          question_id: questionId,
          selected_index: index,
          client_event_id: crypto.randomUUID(),
        };

        const response = await submitAnswerThin(sessionId, payload);

        // Update cache with server response
        mutateQuestion(
          {
            ...currentQuestionData,
            answer_state: response.answer_state,
          },
          false,
        );

        // Update state (increment answered_count if this was a new answer)
        mutateState(
          (state) =>
            state && currentQuestionData.answer_state.selected_index === null
              ? {
                  ...state,
                  answered_count: state.answered_count + 1,
                }
              : state,
          false,
        );

        track("ANSWER_CHANGED", {
          question_id: questionId,
          from: currentQuestionData.answer_state.selected_index,
          to: index,
        });
      } catch (err) {
        console.error("Failed to save answer:", err);
        notify.error("Failed to save answer", "Please try again");

        // Revert optimistic update
        mutateQuestion(currentQuestionData, false);
      } finally {
        setSavingAnswer(false);
      }
    },
    [currentQuestionData, currentPosition, sessionId, mutateQuestion, mutateState, track],
  );

  // Handle mark for review
  const handleToggleMarkForReview = useCallback(
    async (questionId: string, marked: boolean) => {
      if (!currentQuestionData) return;

      // Optimistic update
      const optimisticData: QuestionWithAnswerState = {
        ...currentQuestionData,
        answer_state: {
          ...currentQuestionData.answer_state,
          marked_for_review: marked,
        },
      };
      mutateQuestion(optimisticData, false);

      try {
        const payload: AnswerSubmitThinRequest = {
          index: currentPosition,
          question_id: questionId,
          marked_for_review: marked,
          client_event_id: crypto.randomUUID(),
        };

        const response = await submitAnswerThin(sessionId, payload);

        // Update cache
        mutateQuestion(
          {
            ...currentQuestionData,
            answer_state: response.answer_state,
          },
          false,
        );

        track("MARK_FOR_REVIEW_TOGGLED", { question_id: questionId, marked });
      } catch (err) {
        console.error("Failed to update mark for review:", err);
        notify.error("Failed to update", "Please try again");

        // Revert
        mutateQuestion(currentQuestionData, false);
      }
    },
    [currentQuestionData, currentPosition, sessionId, mutateQuestion, track],
  );

  // Handle navigation
  const handleNavigate = useCallback(
    (position: number) => {
      track("NAVIGATE_JUMP", { from_position: currentPosition, to_position: position });
      // Update state optimistically
      mutateState(
        (state) =>
          state
            ? {
                ...state,
                current_index: position,
              }
            : undefined,
        false,
      );
      setShowMobileNav(false);
    },
    [currentPosition, track, mutateState],
  );

  const handlePrevious = useCallback(() => {
    if (currentPosition > 1) {
      track("NAVIGATE_PREV", { from_position: currentPosition, to_position: currentPosition - 1 });
      handleNavigate(currentPosition - 1);
    }
  }, [currentPosition, track, handleNavigate]);

  const handleNext = useCallback(() => {
    if (sessionState && currentPosition < sessionState.total_questions) {
      track("NAVIGATE_NEXT", { from_position: currentPosition, to_position: currentPosition + 1 });
      handleNavigate(currentPosition + 1);
    }
  }, [currentPosition, sessionState, track, handleNavigate]);

  const handleSubmitClick = useCallback(() => {
    setShowSubmitDialog(true);
  }, []);

  const handleSubmitConfirmed = useCallback(async () => {
    try {
      // Flush telemetry before submit
      await flush();

      const response = await submitSessionThin(sessionId);
      notify.success("Session submitted", "Your test has been submitted successfully");
      router.push(response.review_url.replace("/v1", "/student/session"));
    } catch (err: unknown) {
      console.error("Failed to submit session:", err);
      const error = err as { message?: string };
      notify.error("Failed to submit session", error.message || "Please try again");
    } finally {
      setShowSubmitDialog(false);
    }
  }, [sessionId, flush, router]);

  // Loading state
  if (stateLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-16 w-full" />
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="space-y-6 lg:col-span-2">
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-96 w-full" />
            </div>
            <div className="hidden lg:block">
              <Skeleton className="h-96 w-full" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (stateError || !sessionState) {
    const errorMessage =
      (stateError as { message?: string })?.message ||
      (stateError as { status?: number })?.status === 404
        ? "Session not found"
        : "Failed to load session";
    return (
      <div className="container mx-auto max-w-2xl px-4 py-8">
        <InlineAlert variant="error" message={errorMessage} />
        <Button onClick={() => router.push("/student/dashboard")} className="mt-4">
          Back to Dashboard
        </Button>
      </div>
    );
  }

  // Build question summaries for navigator
  // Use real question IDs from current question and prefetched questions when available
  const questionSummaries = useMemo<SessionQuestionSummary[]>(() => {
    const summaries: SessionQuestionSummary[] = [];
    const questionIdMap = new Map<number, string>();
    const answerStateMap = new Map<number, { has_answer: boolean; marked_for_review: boolean }>();
    
    // Add current question if available
    if (currentQuestionData) {
      questionIdMap.set(currentQuestionData.index, currentQuestionData.question.question_id);
      answerStateMap.set(currentQuestionData.index, {
        has_answer: currentQuestionData.answer_state.selected_index !== null,
        marked_for_review: currentQuestionData.answer_state.marked_for_review,
      });
    }
    
    // Build summaries for all questions
    for (let i = 1; i <= sessionState.total_questions; i++) {
      const questionId = questionIdMap.get(i) || `temp-${sessionId}-${i}`;
      const answerState = answerStateMap.get(i) || { has_answer: false, marked_for_review: false };
      
      summaries.push({
        position: i,
        question_id: questionId,
        has_answer: answerState.has_answer,
        marked_for_review: answerState.marked_for_review,
      });
    }
    
    return summaries;
  }, [sessionState.total_questions, sessionId, currentQuestionData]);

  // Convert QuestionThin to CurrentQuestion format for QuestionView component
  const currentQuestionForView = useMemo(() => {
    if (!currentQuestionData) return null;

    const q = currentQuestionData.question;
    return {
      question_id: q.question_id,
      position: currentQuestionData.index,
      stem: q.stem,
      option_a: q.options[0] || "",
      option_b: q.options[1] || "",
      option_c: q.options[2] || "",
      option_d: q.options[3] || "",
      option_e: q.options[4] || "",
    };
  }, [currentQuestionData]);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top Bar */}
      <SessionTopBar
        mode={sessionState.mode}
        expiresAt={
          sessionState.time_limit_seconds
            ? new Date(Date.now() + sessionState.time_limit_seconds * 1000).toISOString()
            : null
        }
        progress={{
          answered_count: sessionState.answered_count,
          marked_for_review_count: 0, // Would need separate query or include in state
          current_position: sessionState.current_index,
        }}
        totalQuestions={sessionState.total_questions}
        onSubmit={handleSubmitClick}
        onExpire={handleExpire}
      />

      {/* Main Content */}
      <div className="container mx-auto flex-1 px-4 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Question View (Left) */}
          <div className="lg:col-span-2">
            {/* Mobile Nav Toggle */}
            <div className="mb-4 lg:hidden">
              <Sheet open={showMobileNav} onOpenChange={setShowMobileNav}>
                <SheetTrigger asChild>
                  <Button variant="outline" className="w-full">
                    <Menu className="mr-2 h-4 w-4" />
                    Question Navigator
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-80">
                  <SheetHeader>
                    <SheetTitle>Questions</SheetTitle>
                  </SheetHeader>
                  <div className="mt-6">
                    <QuestionNavigator
                      questions={questionSummaries}
                      currentPosition={currentPosition}
                      onNavigate={handleNavigate}
                    />
                  </div>
                </SheetContent>
              </Sheet>
            </div>

            {/* Question View */}
            {questionLoading && !currentQuestionData ? (
              <Skeleton className="h-96 w-full" />
            ) : currentQuestionForView && currentQuestionData ? (
              <QuestionView
                question={currentQuestionForView}
                selectedIndex={currentQuestionData.answer_state.selected_index}
                isMarkedForReview={currentQuestionData.answer_state.marked_for_review}
                isSaving={savingAnswer}
                totalQuestions={sessionState.total_questions}
                onSelectOption={(index) =>
                  handleSelectOption(currentQuestionData.question.question_id, index)
                }
                onToggleMarkForReview={(marked) =>
                  handleToggleMarkForReview(currentQuestionData.question.question_id, marked)
                }
                onPrevious={handlePrevious}
                onNext={handleNext}
                canGoPrevious={currentPosition > 1}
                canGoNext={currentPosition < sessionState.total_questions}
              />
            ) : (
              <InlineAlert variant="error" message="Question not found" />
            )}
          </div>

          {/* Navigator (Right) - Desktop Only */}
          <div className="hidden lg:block">
            <div className="sticky top-24">
              <QuestionNavigator
                questions={questionSummaries}
                currentPosition={currentPosition}
                onNavigate={handleNavigate}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Submit Confirmation Dialog */}
      <SubmitConfirmDialog
        open={showSubmitDialog}
        onOpenChange={setShowSubmitDialog}
        onConfirm={handleSubmitConfirmed}
        answeredCount={sessionState.answered_count}
        totalQuestions={sessionState.total_questions}
        markedCount={0} // Would need separate query or include in state
      />
    </div>
  );
}
