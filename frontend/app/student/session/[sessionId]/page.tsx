"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Menu } from "lucide-react";
import { notify } from "@/lib/notify";
import { getSession, submitAnswer, submitSession } from "@/lib/api/sessionsApi";
import type { SessionState, SubmitAnswerRequest } from "@/lib/types/session";
import { SessionTopBar } from "@/components/student/session/SessionTopBar";
import { QuestionNavigator } from "@/components/student/session/QuestionNavigator";
import { QuestionView } from "@/components/student/session/QuestionView";
import { SubmitConfirmDialog } from "@/components/student/session/SubmitConfirmDialog";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { useTelemetry } from "@/lib/hooks/useTelemetry";

export default function SessionPlayerPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  // Telemetry
  const { track, flush } = useTelemetry(sessionId);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [currentPosition, setCurrentPosition] = useState(1);
  const [savingAnswer, setSavingAnswer] = useState(false);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [showMobileNav, setShowMobileNav] = useState(false);

  // Local answer state for optimistic updates
  const [localAnswers, setLocalAnswers] = useState<
    Map<string, { selected_index: number | null; marked_for_review: boolean }>
  >(new Map());

  // Load session
  useEffect(() => {
    loadSession();
  }, [sessionId]);

  // Update current position from progress
  useEffect(() => {
    if (sessionState) {
      setCurrentPosition(sessionState.progress.current_position);
    }
  }, [sessionState]);

  // Track question view when position changes
  useEffect(() => {
    if (sessionState && currentPosition > 0) {
      const currentQuestion = sessionState.questions.find((q) => q.position === currentPosition);
      if (currentQuestion) {
        track("QUESTION_VIEWED", { position: currentPosition }, currentQuestion.question_id);
      }
    }
  }, [currentPosition, sessionState, track]);

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

  async function loadSession() {
    setLoading(true);
    setError(null);

    try {
      const state = await getSession(sessionId);

      // Check if session is no longer active
      if (state.session.status !== "ACTIVE") {
        router.push(`/student/session/${sessionId}/review`);
        return;
      }

      setSessionState(state);

      // Initialize local answers from questions
      const answers = new Map<
        string,
        { selected_index: number | null; marked_for_review: boolean }
      >();
      state.questions.forEach((q) => {
        answers.set(q.question_id, {
          selected_index: null, // Will be populated by backend if exists
          marked_for_review: q.marked_for_review,
        });
      });
      setLocalAnswers(answers);
    } catch (err: unknown) {
      console.error("Failed to load session:", err);

      const error = err as { status?: number; message?: string };
      if (error.status === 404) {
        setError("Session not found");
      } else if (error.status === 403) {
        setError("You don't have permission to access this session");
      } else {
        setError(error.message || "Failed to load session");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleExpire() {
    notify.info("Time's up!", "Your session has expired and will be submitted automatically");
    handleSubmitConfirmed();
  }

  async function handleSelectOption(questionId: string, index: number) {
    // Optimistic update
    setLocalAnswers((prev) => {
      const newMap = new Map(prev);
      const current = newMap.get(questionId) || { selected_index: null, marked_for_review: false };
      newMap.set(questionId, { ...current, selected_index: index });
      return newMap;
    });

    setSavingAnswer(true);

    try {
      const payload: SubmitAnswerRequest = {
        question_id: questionId,
        selected_index: index,
      };

      const response = await submitAnswer(sessionId, payload);

      // Update session state with new progress
      if (sessionState) {
        setSessionState({
          ...sessionState,
          progress: response.progress,
          questions: sessionState.questions.map((q) =>
            q.question_id === questionId ? { ...q, has_answer: true } : q,
          ),
        });
      }
    } catch (err: unknown) {
      console.error("Failed to save answer:", err);
      const error = err as { message?: string };
      notify.error("Failed to save answer", error.message || "Please try again");

      // Revert optimistic update
      setLocalAnswers((prev) => {
        const newMap = new Map(prev);
        const current = newMap.get(questionId);
        if (current) {
          newMap.set(questionId, { ...current, selected_index: null });
        }
        return newMap;
      });
    } finally {
      setSavingAnswer(false);
    }
  }

  async function handleToggleMarkForReview(questionId: string, marked: boolean) {
    // Optimistic update
    setLocalAnswers((prev) => {
      const newMap = new Map(prev);
      const current = newMap.get(questionId) || { selected_index: null, marked_for_review: false };
      newMap.set(questionId, { ...current, marked_for_review: marked });
      return newMap;
    });

    try {
      const payload: SubmitAnswerRequest = {
        question_id: questionId,
        marked_for_review: marked,
      };

      const response = await submitAnswer(sessionId, payload);

      // Update session state
      if (sessionState) {
        setSessionState({
          ...sessionState,
          progress: response.progress,
          questions: sessionState.questions.map((q) =>
            q.question_id === questionId ? { ...q, marked_for_review: marked } : q,
          ),
        });
      }
    } catch (err: unknown) {
      console.error("Failed to update mark for review:", err);

      // Revert optimistic update
      setLocalAnswers((prev) => {
        const newMap = new Map(prev);
        const current = newMap.get(questionId);
        if (current) {
          newMap.set(questionId, { ...current, marked_for_review: !marked });
        }
        return newMap;
      });
    }
  }

  function handleNavigate(position: number) {
    track("NAVIGATE_JUMP", { from_position: currentPosition, to_position: position });
    setCurrentPosition(position);
    setShowMobileNav(false);
  }

  function handlePrevious() {
    if (currentPosition > 1) {
      track("NAVIGATE_PREV", { from_position: currentPosition, to_position: currentPosition - 1 });
      setCurrentPosition(currentPosition - 1);
    }
  }

  function handleNext() {
    if (sessionState && currentPosition < sessionState.session.total_questions) {
      track("NAVIGATE_NEXT", { from_position: currentPosition, to_position: currentPosition + 1 });
      setCurrentPosition(currentPosition + 1);
    }
  }

  function handleSubmitClick() {
    setShowSubmitDialog(true);
  }

  async function handleSubmitConfirmed() {
    try {
      // Flush telemetry before submit
      await flush();

      await submitSession(sessionId);
      notify.success("Session submitted", "Your test has been submitted successfully");
      router.push(`/student/session/${sessionId}/review`);
    } catch (err: unknown) {
      console.error("Failed to submit session:", err);
      const error = err as { message?: string };
      notify.error("Failed to submit session", error.message || "Please try again");
    } finally {
      setShowSubmitDialog(false);
    }
  }

  if (loading) {
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

  if (error || !sessionState) {
    return (
      <div className="container mx-auto max-w-2xl px-4 py-8">
        <InlineAlert variant="error" message={error || "Session not found"} />
        <Button onClick={() => router.push("/student/dashboard")} className="mt-4">
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const currentQuestion =
    sessionState.current_question ||
    sessionState.questions.find((q) => q.position === currentPosition);
  if (!currentQuestion || !sessionState.current_question) {
    return (
      <div className="container mx-auto max-w-2xl px-4 py-8">
        <InlineAlert variant="error" message="Current question not found" />
      </div>
    );
  }

  const localAnswer = localAnswers.get(currentQuestion.question_id);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top Bar */}
      <SessionTopBar
        mode={sessionState.session.mode}
        expiresAt={sessionState.session.expires_at}
        progress={sessionState.progress}
        totalQuestions={sessionState.session.total_questions}
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
                      questions={sessionState.questions}
                      currentPosition={currentPosition}
                      onNavigate={handleNavigate}
                    />
                  </div>
                </SheetContent>
              </Sheet>
            </div>

            <QuestionView
              question={sessionState.current_question}
              selectedIndex={localAnswer?.selected_index ?? null}
              isMarkedForReview={localAnswer?.marked_for_review ?? false}
              isSaving={savingAnswer}
              totalQuestions={sessionState.session.total_questions}
              onSelectOption={(index) => handleSelectOption(currentQuestion.question_id, index)}
              onToggleMarkForReview={(marked) =>
                handleToggleMarkForReview(currentQuestion.question_id, marked)
              }
              onPrevious={handlePrevious}
              onNext={handleNext}
              canGoPrevious={currentPosition > 1}
              canGoNext={currentPosition < sessionState.session.total_questions}
            />
          </div>

          {/* Navigator (Right) - Desktop Only */}
          <div className="hidden lg:block">
            <div className="sticky top-24">
              <QuestionNavigator
                questions={sessionState.questions}
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
        answeredCount={sessionState.progress.answered_count}
        totalQuestions={sessionState.session.total_questions}
        markedCount={sessionState.progress.marked_for_review_count}
      />
    </div>
  );
}
