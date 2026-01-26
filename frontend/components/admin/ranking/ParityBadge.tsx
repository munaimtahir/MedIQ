"use client";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { CheckCircle2, XCircle } from "lucide-react";

const DEFAULT_EPSILON = 0.001;

interface ParityBadgeProps {
  parityReport: {
    max_abs_percentile_diff?: number | null;
    count_mismatch_ranks?: number | null;
  } | null;
  epsilon?: number | null;
  /** If true, show compact badge only; no tooltip. */
  compact?: boolean;
}

export function ParityBadge({ parityReport, epsilon, compact }: ParityBadgeProps) {
  const eps = epsilon ?? DEFAULT_EPSILON;
  const maxDiff = parityReport?.max_abs_percentile_diff ?? null;
  const mismatchCount = parityReport?.count_mismatch_ranks ?? 0;

  const pass =
    (maxDiff == null || maxDiff <= eps) && (mismatchCount === 0 || mismatchCount == null);

  const label = pass ? "PASS" : "FAIL";
  const tip = `max_abs_percentile_diff: ${maxDiff ?? "—"}, rank_mismatch: ${mismatchCount ?? "—"} (ε=${eps})`;

  const badge = (
    <Badge variant={pass ? "default" : "destructive"} className="gap-1">
      {pass ? (
        <CheckCircle2 className="h-3 w-3" />
      ) : (
        <XCircle className="h-3 w-3" />
      )}
      {label}
    </Badge>
  );

  if (compact) {
    return badge;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent>{tip}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
