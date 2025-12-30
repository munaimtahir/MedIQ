"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { studentAPI, syllabusAPI } from "@/lib/api";
import { Question, Theme } from "@/lib/api";

export default function ThemeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const themeId = Number(params.themeId);
  const [theme, setTheme] = useState<Theme | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      syllabusAPI.getThemes().then((themes) => themes.find((t) => t.id === themeId)),
      studentAPI.getQuestions(themeId),
    ])
      .then(([foundTheme, qs]) => {
        setTheme(foundTheme || null);
        setQuestions(qs);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [themeId]);

  const handleStartPractice = async () => {
    try {
      const session = await studentAPI.createSession({
        theme_id: themeId,
        question_count: Math.min(questions.length, 30),
        time_limit_minutes: 60,
      });
      router.push(`/student/session/${session.id}`);
    } catch (error) {
      console.error("Failed to create session:", error);
      alert("Failed to start practice session");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" onClick={() => router.back()}>
          ← Back
        </Button>
        <h1 className="mt-4 text-3xl font-bold">{theme?.name || "Theme"}</h1>
        <p className="text-muted-foreground">{theme?.description}</p>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Practice Options</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="mb-2 text-sm text-muted-foreground">
                  {questions.length} questions available
                </p>
                <Button onClick={handleStartPractice} size="lg" className="w-full">
                  Start Practice Session
                </Button>
              </div>
            </CardContent>
          </Card>

          <div>
            <h2 className="mb-4 text-2xl font-semibold">Sample Questions</h2>
            <div className="space-y-4">
              {questions.slice(0, 3).map((q) => (
                <Card key={q.id}>
                  <CardHeader>
                    <CardTitle className="text-base">{q.question_text}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                      {q.options.map((opt, idx) => (
                        <li key={idx}>{opt}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
