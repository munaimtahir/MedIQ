"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Block } from "@/lib/api";
import { BookOpen, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface BlockProgressCardProps {
  blocks: Block[];
  loading?: boolean;
  error?: Error | null;
}

export function BlockProgressCard({ blocks, loading, error }: BlockProgressCardProps) {
  const router = useRouter();

  if (loading) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-32 mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-2 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle>Block Progress</CardTitle>
          <CardDescription>Your progress by block</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Unable to load blocks. Please try again later.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (blocks.length === 0) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle>Block Progress</CardTitle>
          <CardDescription>Your progress by block</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No blocks available. Complete onboarding to get started.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Mock progress for now (will be replaced with real data later)
  const getMockProgress = (blockId: number) => {
    return Math.floor((blockId % 3) * 33 + 10);
  };

  return (
    <Card className="col-span-full md:col-span-1">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Block Progress
        </CardTitle>
        <CardDescription>Your progress by block</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {blocks.map((block) => {
          const progress = getMockProgress(block.id);
          return (
            <div key={block.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{block.name}</p>
                  <p className="text-xs text-muted-foreground">Code: {block.code}</p>
                </div>
                <span className="text-xs text-muted-foreground">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/student/blocks/${block.id}`)}
                >
                  <BookOpen className="mr-1 h-3 w-3" />
                  Open
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/student/practice/build?block=${block.id}`)}
                >
                  <Play className="mr-1 h-3 w-3" />
                  Practice
                </Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
