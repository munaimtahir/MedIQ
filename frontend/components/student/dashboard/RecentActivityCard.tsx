"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RecentSession } from "@/lib/dashboard/types";
import { History, Play, CheckCircle2, Clock } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface RecentActivityCardProps {
  recentSessions: RecentSession[];
  loading?: boolean;
  error?: Error | null;
}

export function RecentActivityCard({ recentSessions, loading, error }: RecentActivityCardProps) {
  const router = useRouter();

  if (loading) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Your recent practice sessions</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Unable to load recent activity. Start a practice session to see it here.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (recentSessions.length === 0) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Recent Activity
          </CardTitle>
          <CardDescription>Your recent practice sessions</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            No recent sessions. Start practicing to see your activity here.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/student/practice/build")}
          >
            <Play className="mr-2 h-4 w-4" />
            Start Practice
          </Button>
        </CardContent>
      </Card>
    );
  }

  const getStatusBadge = (status: RecentSession["status"]) => {
    switch (status) {
      case "completed":
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        );
      case "in_progress":
        return (
          <Badge variant="default" className="bg-blue-500">
            <Clock className="mr-1 h-3 w-3" />
            In Progress
          </Badge>
        );
      case "abandoned":
        return <Badge variant="secondary">Abandoned</Badge>;
      default:
        return null;
    }
  };

  return (
    <Card className="col-span-full md:col-span-1">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Recent Activity
        </CardTitle>
        <CardDescription>Your last 5 practice sessions</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {recentSessions.slice(0, 5).map((session) => (
          <div
            key={session.id}
            className="flex items-center justify-between rounded-lg border p-3"
          >
            <div className="flex-1">
              <p className="font-medium text-sm">{session.title}</p>
              <div className="flex items-center gap-2 mt-1">
                {getStatusBadge(session.status)}
                {session.score !== undefined && (
                  <span className="text-xs text-muted-foreground">
                    Score: {session.score}/{session.scorePercentage}%
                  </span>
                )}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push(session.href)}
            >
              {session.status === "in_progress" ? (
                <>
                  <Play className="mr-1 h-4 w-4" />
                  Resume
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-1 h-4 w-4" />
                  Review
                </>
              )}
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
