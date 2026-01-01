"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { onboardingAPI, UserProfile, UserProfileBlock } from "@/lib/api";
import { useRouter } from "next/navigation";
import { BookOpen, TrendingUp, Clock, Target } from "lucide-react";
import { SkeletonCardGrid } from "@/components/status/SkeletonCardGrid";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";

export default function StudentDashboard() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadProfile = () => {
    setLoading(true);
    setError(null);
    onboardingAPI
      .getProfile()
      .then(setProfile)
      .catch((err) => {
        console.error("Failed to load profile:", err);
        setError(err instanceof Error ? err : new Error("Failed to load profile"));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const blocks = profile?.selected_blocks || [];
  const yearName = profile?.selected_year?.display_name || "Your";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back! Continue your practice.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Questions</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">30</div>
            <p className="text-xs text-muted-foreground">Available for practice</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Complete a session to see</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Time Spent</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">This week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Target</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Questions per day</p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="mb-4 text-2xl font-semibold">{yearName} Blocks</h2>
        {loading ? (
          <SkeletonCardGrid cards={3} />
        ) : error ? (
          <ErrorState
            variant="card"
            title="Failed to load profile"
            description={error.message || "An error occurred while loading your profile."}
            actionLabel="Retry"
            onAction={loadProfile}
          />
        ) : blocks.length === 0 ? (
          <EmptyState
            variant="card"
            title="No blocks selected"
            description="Complete onboarding to select your blocks and start practicing."
            icon={<BookOpen className="h-8 w-8 text-slate-400" />}
            actionLabel="Go to Onboarding"
            onAction={() => router.push("/onboarding")}
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {blocks.map((block) => (
              <Card key={block.id} className="cursor-pointer transition-shadow hover:shadow-lg">
                <CardHeader>
                  <CardTitle>{block.display_name}</CardTitle>
                  <CardDescription>Block {block.code}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    onClick={() => router.push(`/student/blocks/${block.id}`)}
                    className="w-full"
                  >
                    View Block
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Start</CardTitle>
          <CardDescription>Start a practice session</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => router.push("/student/practice/build")} size="lg">
            Start Practice Session
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
