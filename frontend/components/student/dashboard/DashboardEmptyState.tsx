"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BookOpen, PlayCircle, Target } from "lucide-react";
import { useRouter } from "next/navigation";

export function DashboardEmptyState() {
  const router = useRouter();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Welcome! Let's get you started.</p>
      </div>

      {/* Getting Started Card */}
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            Getting Started
          </CardTitle>
          <CardDescription>Follow these steps to begin your practice</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-start gap-4 rounded-lg border p-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                1
              </div>
              <div className="flex-1">
                <h3 className="font-medium">Pick your year and blocks</h3>
                <p className="text-sm text-muted-foreground">
                  Complete onboarding to select your academic year and blocks.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => router.push("/onboarding")}
                >
                  <BookOpen className="mr-2 h-4 w-4" />
                  Go to Onboarding
                </Button>
              </div>
            </div>

            <div className="flex items-start gap-4 rounded-lg border p-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                2
              </div>
              <div className="flex-1">
                <h3 className="font-medium">Try a quick practice</h3>
                <p className="text-sm text-muted-foreground">
                  Start with a 10-question practice session to get familiar with the platform.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => router.push("/student/practice/build?preset=tutor&count=10")}
                >
                  <PlayCircle className="mr-2 h-4 w-4" />
                  Start 10-Question Practice
                </Button>
              </div>
            </div>

            <div className="flex items-start gap-4 rounded-lg border p-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                3
              </div>
              <div className="flex-1">
                <h3 className="font-medium">Review results</h3>
                <p className="text-sm text-muted-foreground">
                  After completing a session, review your results to identify weak themes.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
