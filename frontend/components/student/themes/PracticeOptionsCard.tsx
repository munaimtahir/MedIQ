"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Play, Clock, Layers } from "lucide-react";
import { useRouter } from "next/navigation";

interface PracticeOptionsCardProps {
  themeId: number;
  blockId: number;
  isAllowed?: boolean; // Deprecated - always true now
  allowedBlockIds?: number[]; // Deprecated - no longer used
}

export function PracticeOptionsCard({
  themeId,
  blockId,
  isAllowed: _isAllowed, // eslint-disable-line @typescript-eslint/no-unused-vars
  allowedBlockIds: _allowedBlockIds, // eslint-disable-line @typescript-eslint/no-unused-vars
}: PracticeOptionsCardProps) {
  const router = useRouter();

  const handlePractice = (mode: "tutor" | "exam" | "mixed") => {
    let url = `/student/practice/build?mode=${mode}&theme_ids=${themeId}`;

    if (mode === "mixed") {
      // Include block ID for mixed practice
      url += `&block_id=${blockId}`;
    }

    router.push(url);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Practice Options</CardTitle>
        <CardDescription>Choose how you want to practice this theme</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button
          variant="default"
          className="w-full justify-start"
          onClick={() => handlePractice("tutor")}
        >
          <Play className="mr-2 h-4 w-4" />
          Practice this theme
        </Button>

        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => handlePractice("exam")}
        >
          <Clock className="mr-2 h-4 w-4" />
          Timed practice (exam mode)
        </Button>

        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => handlePractice("mixed")}
        >
          <Layers className="mr-2 h-4 w-4" />
          Mixed practice (this theme + block)
        </Button>
      </CardContent>
    </Card>
  );
}
