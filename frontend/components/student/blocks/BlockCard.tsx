"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Block, Theme, syllabusAPI } from "@/lib/api";
import { BookOpen, Play } from "lucide-react";
import { useRouter } from "next/navigation";
// Tooltip component not available, using title attribute instead

interface BlockCardProps {
  block: Block;
  isAllowed?: boolean; // Deprecated - always true now
  loading?: boolean;
}

export function BlockCard({ block, isAllowed: _isAllowed, loading }: BlockCardProps) {
  const router = useRouter();
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loadingThemes, setLoadingThemes] = useState(false);
  const [showAllThemes, setShowAllThemes] = useState(false);

  useEffect(() => {
    loadThemes();
  }, [block.id]);

  async function loadThemes() {
    setLoadingThemes(true);
    try {
      const themesData = await syllabusAPI.getThemes(block.id);
      setThemes(themesData);
    } catch (error) {
      console.error("Failed to load themes:", error);
      setThemes([]);
    } finally {
      setLoadingThemes(false);
    }
  }

  const displayedThemes = showAllThemes ? themes : themes.slice(0, 6);
  const remainingCount = themes.length - 6;

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="transition-shadow hover:shadow-lg">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>
              Block {block.code}: {block.name}
            </CardTitle>
            <CardDescription className="mt-1">
              {themes.length} {themes.length === 1 ? "theme" : "themes"}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar - not available yet */}
        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="text-muted-foreground text-xs">Not available yet</span>
          </div>
          <Progress value={0} className="opacity-50" />
          <p className="text-xs text-muted-foreground">
            Progress will appear after the test engine is enabled
          </p>
        </div>

        {/* Themes preview */}
        {loadingThemes ? (
          <div className="space-y-2">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
          </div>
        ) : themes.length > 0 ? (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {displayedThemes.map((theme) => (
                <Badge
                  key={theme.id}
                  variant="outline"
                  className="cursor-pointer hover:bg-accent"
                  onClick={() =>
                    router.push(`/student/blocks/${block.id}/themes/${theme.id}`)
                  }
                >
                  {theme.title}
                </Badge>
              ))}
              {themes.length > 6 && !showAllThemes && (
                <Badge
                  variant="outline"
                  className="cursor-pointer hover:bg-accent"
                  onClick={() => setShowAllThemes(true)}
                >
                  +{remainingCount} more
                </Badge>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No themes available</p>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => router.push(`/student/blocks/${block.id}`)}
          >
            <BookOpen className="mr-2 h-4 w-4" />
            Open Block
          </Button>
          <Button
            variant="default"
            className="flex-1"
            onClick={() => {
              router.push(
                `/student/practice/build?year_id=${block.year_id}&block_ids=${block.id}`
              );
            }}
          >
            <Play className="mr-2 h-4 w-4" />
            Practice Block
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
