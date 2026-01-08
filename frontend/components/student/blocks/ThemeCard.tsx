"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Theme } from "@/lib/api";
import { Play, BookOpen } from "lucide-react";
import { useRouter } from "next/navigation";

interface ThemeCardProps {
  theme: Theme;
  index: number;
  total: number;
  isBlockAllowed?: boolean; // Deprecated - always true now
}

export function ThemeCard({ theme, index, total, isBlockAllowed }: ThemeCardProps) {
  const router = useRouter();

  return (
    <Card className="transition-shadow hover:shadow-lg">
      <CardHeader>
        <CardTitle className="text-lg">{theme.title}</CardTitle>
        <CardDescription>
          Theme {index + 1} of {total}
        </CardDescription>
        {theme.description && (
          <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
            {theme.description}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-2">
        <Button
          variant="default"
          className="w-full"
          onClick={() => {
            router.push(
              `/student/practice/build?theme_ids=${theme.id}&block_id=${theme.block_id}`
            );
          }}
        >
          <Play className="mr-2 h-4 w-4" />
          Practice this theme
        </Button>
        <Button
          variant="outline"
          className="w-full"
          onClick={() => router.push(`/student/blocks/${theme.block_id}/themes/${theme.id}`)}
        >
          <BookOpen className="mr-2 h-4 w-4" />
          View details
        </Button>
      </CardContent>
    </Card>
  );
}
