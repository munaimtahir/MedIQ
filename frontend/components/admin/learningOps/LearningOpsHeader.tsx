"use client";

import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "@/lib/dateUtils";
import type { RuntimeStatus } from "@/lib/api/adminLearningOps";

interface LearningOpsHeaderProps {
  runtime: RuntimeStatus | null;
  safeToActivate: "safe" | "caution" | "unsafe";
  loading?: boolean;
}

export function LearningOpsHeader({ runtime, safeToActivate, loading }: LearningOpsHeaderProps) {
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-muted animate-pulse rounded w-48" />
        <div className="flex gap-2">
          <div className="h-6 bg-muted animate-pulse rounded w-32" />
          <div className="h-6 bg-muted animate-pulse rounded w-32" />
        </div>
      </div>
    );
  }

  const profile = runtime?.config.active_profile || "V1_PRIMARY";
  const isFrozen = runtime?.config.safe_mode.freeze_updates || false;
  const activeSince = runtime?.active_since;

  const safeBadgeVariant =
    safeToActivate === "safe" ? "default" : safeToActivate === "caution" ? "secondary" : "destructive";
  const safeBadgeText =
    safeToActivate === "safe"
      ? "Ops stable"
      : safeToActivate === "caution"
        ? "Caution"
        : "Unsafe";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Learning Ops</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Runtime control, shadow systems, activation gates, and health
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Active profile:</span>
          <Badge variant={profile === "V1_PRIMARY" ? "default" : "secondary"}>{profile}</Badge>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Freeze updates:</span>
          <Badge variant={isFrozen ? "destructive" : "default"}>{isFrozen ? "ON" : "OFF"}</Badge>
        </div>

        {activeSince && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Last switch:</span>
            <span className="text-sm">
              {formatDistanceToNow(new Date(activeSince), { addSuffix: true })}
            </span>
          </div>
        )}

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <Badge variant={safeBadgeVariant}>{safeBadgeText}</Badge>
        </div>
      </div>
    </div>
  );
}
