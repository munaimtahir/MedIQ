"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { studentAPI } from "@/lib/api";
import { Session, Question } from "@/lib/api";
import { Clock, Flag } from "lucide-react";

export default function TestPlayerPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.sessionId);
  const [session, setSession] = useState<Session | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [markedForReview, setMarkedForReview] = useState(false);
  const [answers, setAnswers] = useState<Record<number, { option: number; marked: boolean }>>({});
  const [timeRemaining, setTimeRemaining] = useState(3600); // seconds
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      studentAPI.getSession(sessionId),
      studentAPI.getQuestions(undefined, undefined, 100),
    ])
      .then(([sess, qs]) => {
        setSession(sess);
        // Filter questions to only those in session
        const sessionQuestions = qs.filter((q) => sess.question_ids.includes(q.id));
        setQuestions(sessionQuestions);
        // Load existing answers
        const existingAnswers: Record<number, { option: number; marked: boolean }> = {};
        sessionQuestions.forEach((q) => {
          existingAnswers[q.id] = { option: -1, marked: false };
        });
        setAnswers(existingAnswers);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => {
    if (timeRemaining > 0 && !session?.is_submitted) {
      const timer = setInterval(() => {
        setTimeRemaining((prev) => Math.max(0, prev - 1));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [timeRemaining, session?.is_submitted]);

  const currentQuestion = questions[currentIndex];

  const handleOptionSelect = (optionIndex: number) => {
    setSelectedOption(optionIndex);
    if (currentQuestion) {
      const newAnswers = {
        ...answers,
        [currentQuestion.id]: { option: optionIndex, marked: markedForReview },
      };
      setAnswers(newAnswers);
    }
  };

  const handleMarkForReview = () => {
    const newMarked = !markedForReview;
    setMarkedForReview(newMarked);
    if (currentQuestion) {
      const newAnswers = {
        ...answers,
        [currentQuestion.id]: {
          option: selectedOption ?? -1,
          marked: newMarked,
        },
      };
      setAnswers(newAnswers);
    }
  };

  const handleSaveAnswer = async () => {
    if (!currentQuestion || selectedOption === null) return;

    try {
      await studentAPI.submitAnswer(sessionId, {
        question_id: currentQuestion.id,
        selected_option_index: selectedOption,
        is_marked_for_review: markedForReview,
      });
    } catch (error) {
      console.error("Failed to save answer:", error);
    }
  };

  const handleNext = () => {
    handleSaveAnswer();
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      const nextQ = questions[currentIndex + 1];
      const nextAnswer = answers[nextQ.id];
      setSelectedOption(nextAnswer?.option !== -1 ? nextAnswer.option : null);
      setMarkedForReview(nextAnswer?.marked || false);
    }
  };

  const handlePrevious = () => {
    handleSaveAnswer();
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      const prevQ = questions[currentIndex - 1];
      const prevAnswer = answers[prevQ.id];
      setSelectedOption(prevAnswer?.option !== -1 ? prevAnswer.option : null);
      setMarkedForReview(prevAnswer?.marked || false);
    }
  };

  const handleSubmit = async () => {
    if (!confirm("Are you sure you want to submit? This cannot be undone.")) return;

    try {
      await studentAPI.submitSession(sessionId);
      router.push(`/student/session/${sessionId}/review`);
    } catch (error) {
      console.error("Failed to submit session:", error);
      alert("Failed to submit session");
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return <div>Loading session...</div>;
  }

  if (!currentQuestion) {
    return <div>No questions found</div>;
  }

  const answeredCount = Object.values(answers).filter((a) => a.option !== -1).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Practice Session</h1>
          <p className="text-muted-foreground">
            Question {currentIndex + 1} of {questions.length}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            <span className="text-lg font-semibold">{formatTime(timeRemaining)}</span>
          </div>
          <Badge variant="secondary">{answeredCount} answered</Badge>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        <div className="col-span-3">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Question {currentIndex + 1}</CardTitle>
                {markedForReview && (
                  <Badge variant="outline">
                    <Flag className="mr-1 h-3 w-3" />
                    Marked for Review
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-lg">{currentQuestion.question_text}</p>
              <div className="space-y-2">
                {currentQuestion.options.map((option, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleOptionSelect(idx)}
                    className={`w-full rounded-md border-2 p-4 text-left transition-colors ${
                      selectedOption === idx
                        ? "border-primary bg-primary/10"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={`flex h-5 w-5 items-center justify-center rounded-full border-2 ${
                          selectedOption === idx ? "border-primary bg-primary" : "border-gray-300"
                        }`}
                      >
                        {selectedOption === idx && (
                          <div className="h-2 w-2 rounded-full bg-white" />
                        )}
                      </div>
                      <span>
                        {String.fromCharCode(65 + idx)}. {option}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handleMarkForReview}
                  className={markedForReview ? "bg-yellow-100" : ""}
                >
                  <Flag className="mr-2 h-4 w-4" />
                  {markedForReview ? "Unmark" : "Mark"} for Review
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button onClick={handlePrevious} disabled={currentIndex === 0}>
              Previous
            </Button>
            {currentIndex === questions.length - 1 ? (
              <Button onClick={handleSubmit} variant="default">
                Submit Session
              </Button>
            ) : (
              <Button onClick={handleNext}>Next</Button>
            )}
          </div>
        </div>

        <div className="col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Question Map</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-5 gap-2">
                {questions.map((q, idx) => {
                  const answer = answers[q.id];
                  const isAnswered = answer?.option !== -1;
                  const isMarked = answer?.marked;
                  const isCurrent = idx === currentIndex;
                  return (
                    <button
                      key={q.id}
                      onClick={() => {
                        handleSaveAnswer();
                        setCurrentIndex(idx);
                        const ans = answers[q.id];
                        setSelectedOption(ans?.option !== -1 ? ans.option : null);
                        setMarkedForReview(ans?.marked || false);
                      }}
                      className={`h-8 w-8 rounded text-xs font-semibold ${
                        isCurrent
                          ? "bg-primary text-primary-foreground"
                          : isAnswered
                            ? isMarked
                              ? "bg-yellow-500 text-white"
                              : "bg-green-500 text-white"
                            : "bg-muted"
                      }`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
