"use client";

import { useParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, ArrowLeft, ArrowRight } from "lucide-react";
import { ThemeHeader } from "@/components/student/themes/ThemeHeader";
import { ThemeOverviewCard } from "@/components/student/themes/ThemeOverviewCard";
import { PracticeOptionsCard } from "@/components/student/themes/PracticeOptionsCard";
import { ThemeSkeleton } from "@/components/student/themes/ThemeSkeleton";
import {
  useBlockData,
  useThemes,
} from "@/lib/blocks/hooks";

export default function ThemeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const blockId = Number(params.blockId);
  const themeId = Number(params.themeId);

  // Fetch block and year data
  const { block, year, loading: loadingBlock, error: blockError } = useBlockData(blockId);

  // Fetch themes for the block
  const { themes, loading: loadingThemes, error: themesError } = useThemes(blockId);

  // Find current theme
  const currentTheme = themes.find((t) => t.id === themeId);

  // Determine next theme
  const sortedThemes = [...themes].sort((a, b) => a.order_no - b.order_no);
  const currentIndex = sortedThemes.findIndex((t) => t.id === themeId);
  const nextTheme = currentIndex >= 0 && currentIndex < sortedThemes.length - 1
    ? sortedThemes[currentIndex + 1]
    : null;

  // Loading state
  if (loadingBlock || loadingThemes) {
    return (
      <div className="max-w-6xl mx-auto">
        <ThemeSkeleton />
      </div>
    );
  }

  // Error state - block not found
  if (blockError || !block) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <Button variant="ghost" onClick={() => router.push("/student/blocks")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Blocks
          </Button>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <div>
                <p className="font-medium">Block not found</p>
                <p className="text-sm text-muted-foreground">
                  The block you're looking for doesn't exist or is no longer available.
                </p>
              </div>
            </div>
            <Button onClick={() => router.push("/student/blocks")} className="mt-4">
              Back to Blocks
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state - theme not found
  if (themesError || !currentTheme) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <Button variant="ghost" onClick={() => router.push(`/student/blocks/${blockId}`)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Block
          </Button>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <div>
                <p className="font-medium">Theme not found</p>
                <p className="text-sm text-muted-foreground">
                  {themesError
                    ? themesError.message
                    : "The theme you're looking for doesn't exist or is no longer available."}
                </p>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <Button
                onClick={() => router.push(`/student/blocks/${blockId}`)}
                variant="outline"
              >
                Back to Block
              </Button>
              <Button onClick={() => router.push("/student/blocks")}>
                Back to Blocks
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <ThemeHeader
        theme={currentTheme}
        block={block}
        yearName={year?.name || "Unknown Year"}
        status="not_available"
      />

      {/* Overview Card */}
      <ThemeOverviewCard theme={currentTheme} block={block} />

      {/* Practice Options */}
      <PracticeOptionsCard
        themeId={currentTheme.id}
        blockId={block.id}
      />

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4 border-t">
        <Button
          variant="ghost"
          onClick={() => router.push(`/student/blocks/${blockId}`)}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Block {block.code}
        </Button>
        {nextTheme && (
          <Button
            variant="ghost"
            onClick={() =>
              router.push(`/student/blocks/${blockId}/themes/${nextTheme.id}`)
            }
          >
            Next theme
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
