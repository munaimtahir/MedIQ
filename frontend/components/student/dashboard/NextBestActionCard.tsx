"use client";

import { memo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { NextAction } from "@/lib/dashboard/types";
import { PlayCircle, ArrowRight, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface NextBestActionCardProps {
  nextAction: NextAction | null;
  loading?: boolean;
  error?: Error | null;
}

export const NextBestActionCard = memo(function NextBestActionCard({ 
  nextAction, 
  loading, 
  error 
}: NextBestActionCardProps) {
  const router = useRouter();

  if (loading) {
    return (
      <Card className="col-span-full md:col-span-2">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="mt-2 h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="mb-2 h-12 w-full" />
          <Skeleton className="h-4 w-56" />
        </CardContent>
      </Card>
    );
  }

  if (error || !nextAction) {
    return (
      <Card className="col-span-full md:col-span-2">
        <CardHeader>
          <CardTitle>Your next best step</CardTitle>
          <CardDescription>Based on your recent activity</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            size="lg"
            className="w-full"
            onClick={() => router.push("/student/practice/build")}
          >
            <PlayCircle className="mr-2 h-5 w-5" />
            Start Quick Practice
          </Button>
          {error && (
            <p className="text-sm text-muted-foreground">
              Some features may be unavailable. You can still start practicing.
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="col-span-full md:col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          Your next best step
        </CardTitle>
        <CardDescription>Based on your recent activity</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button size="lg" className="w-full" onClick={() => router.push(nextAction.href)}>
          <PlayCircle className="mr-2 h-5 w-5" />
          {nextAction.label}
        </Button>

        {nextAction.hint && <p className="text-sm text-muted-foreground">{nextAction.hint}</p>}

        {nextAction.secondaryActions && nextAction.secondaryActions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {nextAction.secondaryActions.map((action, idx) => (
              <Button
                key={idx}
                variant="outline"
                size="sm"
                onClick={() => router.push(action.href)}
              >
                {action.label}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
});
