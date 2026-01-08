"use client";

import { useParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, ArrowLeft, ArrowRight } from "lucide-react";
import { BlockHeader } from "@/components/student/blocks/BlockHeader";
import { BlockOverviewCard } from "@/components/student/blocks/BlockOverviewCard";
import { ThemeCard } from "@/components/student/blocks/ThemeCard";
import { QuickActionsCard } from "@/components/student/blocks/QuickActionsCard";
import { BlockDetailSkeleton } from "@/components/student/blocks/BlockDetailSkeleton";
import {
  useBlockData,
  useThemes,
} from "@/lib/blocks/hooks";
import Link from "next/link";

export default function BlockDetailPage() {
  const params = useParams();
  const router = useRouter();
  const blockId = Number(params.blockId);

  // Fetch block and year data
  const { block, year, loading: loadingBlock, error: blockError } = useBlockData(blockId);

  // Fetch themes
  const { themes, loading: loadingThemes, error: themesError } = useThemes(blockId);

  // Loading state
  if (loadingBlock) {
    return (
      <div className="max-w-6xl mx-auto">
        <BlockDetailSkeleton />
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

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <BlockHeader
        block={block}
        yearName={year?.name || "Unknown Year"}
        status="not_available"
      />

      {/* Overview Card */}
      <BlockOverviewCard
        block={block}
        themeCount={themes.length}
      />

      {/* Themes Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-2xl font-bold">Themes</h2>
          <p className="text-muted-foreground">Choose any theme or practice the entire block</p>
        </div>

        {loadingThemes ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="space-y-2">
                    <div className="h-6 w-3/4 bg-muted animate-pulse rounded" />
                    <div className="h-4 w-1/2 bg-muted animate-pulse rounded" />
                    <div className="h-10 w-full bg-muted animate-pulse rounded mt-4" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : themesError ? (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <div>
                  <p className="font-medium">Error loading themes</p>
                  <p className="text-sm text-muted-foreground">{themesError.message}</p>
                </div>
              </div>
              <Button
                onClick={() => window.location.reload()}
                variant="outline"
                className="mt-4"
              >
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : themes.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <p className="text-center text-muted-foreground">
                No themes have been added to this block yet.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {themes.map((theme, index) => (
              <ThemeCard
                key={theme.id}
                theme={theme}
                index={index}
                total={themes.length}
              />
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <QuickActionsCard
        blockId={block.id}
        yearId={year?.id || 0}
      />

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-4 border-t">
        <Button variant="ghost" onClick={() => router.push("/student/blocks")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Blocks
        </Button>
        {/* Next block navigation could be added here if needed */}
      </div>
    </div>
  );
}
