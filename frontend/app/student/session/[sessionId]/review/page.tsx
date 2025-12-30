"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { studentAPI } from "@/lib/api";
import { ReviewData } from "@/lib/api";
import { CheckCircle2, XCircle, AlertCircle } from "lucide-react";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.sessionId);
  const [review, setReview] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    studentAPI
      .getReview(sessionId)
      .then(setReview)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return <div>Loading review...</div>;
  }

  if (!review) {
    return <div>Review not found</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" onClick={() => router.push("/student/dashboard")}>
          ← Back to Dashboard
        </Button>
        <h1 className="mt-4 text-3xl font-bold">Session Review</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Session Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Total Questions</p>
              <p className="text-2xl font-bold">{review.total_questions}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Correct</p>
              <p className="text-2xl font-bold text-green-600">{review.correct_count}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Incorrect</p>
              <p className="text-2xl font-bold text-red-600">{review.incorrect_count}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Score</p>
              <p className="text-2xl font-bold">{review.score_percentage}%</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {review.questions.map((q, idx) => (
          <Card
            key={q.question_id}
            className={q.is_correct ? "border-green-500" : "border-red-500"}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Question {idx + 1}</CardTitle>
                <div className="flex items-center gap-2">
                  {q.is_correct ? (
                    <Badge variant="success">
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                      Correct
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      <XCircle className="mr-1 h-3 w-3" />
                      Incorrect
                    </Badge>
                  )}
                  {q.is_marked_for_review && (
                    <Badge variant="outline">
                      <AlertCircle className="mr-1 h-3 w-3" />
                      Marked
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="font-medium">{q.question_text}</p>
              <div className="space-y-2">
                {q.options.map((option, optIdx) => {
                  const isCorrect = optIdx === q.correct_option_index;
                  const isSelected = optIdx === q.selected_option_index;
                  return (
                    <div
                      key={optIdx}
                      className={`rounded-md border-2 p-3 ${
                        isCorrect
                          ? "border-green-500 bg-green-50"
                          : isSelected && !isCorrect
                            ? "border-red-500 bg-red-50"
                            : "border-border"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {isCorrect && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                        {isSelected && !isCorrect && <XCircle className="h-4 w-4 text-red-600" />}
                        <span className={isCorrect ? "font-semibold" : ""}>
                          {String.fromCharCode(65 + optIdx)}. {option}
                        </span>
                        {isCorrect && (
                          <Badge variant="success" className="ml-auto">
                            Correct Answer
                          </Badge>
                        )}
                        {isSelected && !isCorrect && (
                          <Badge variant="destructive" className="ml-auto">
                            Your Answer
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              {q.explanation && (
                <div className="mt-4 rounded-md bg-muted p-4">
                  <p className="mb-2 text-sm font-semibold">Explanation:</p>
                  <p className="text-sm">{q.explanation}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
