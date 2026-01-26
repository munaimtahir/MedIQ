"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { JsonViewer } from "@/components/shared/JsonViewer";
import { ParityBadge } from "./ParityBadge";
import type { RankingRunDetail } from "@/lib/api/adminRanking";
import { notify } from "@/lib/notify";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";

interface RunDetailDrawerProps {
  run: RankingRunDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  epsilon?: number | null;
  loading?: boolean;
}

export function RunDetailDrawer({
  run,
  open,
  onOpenChange,
  epsilon,
  loading = false,
}: RunDetailDrawerProps) {
  if (!run && !loading) return null;

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    notify.success("Copied", "Copied to clipboard");
  };

  const pr = run
    ? (run.parity_report as {
        max_abs_percentile_diff?: number | null;
        count_mismatch_ranks?: number | null;
        sample_mismatches?: unknown[] | null;
      } | null)
    : null;
  const sampleMismatches = pr?.sample_mismatches;
  const capped = Array.isArray(sampleMismatches)
    ? sampleMismatches.slice(0, 20)
    : [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>
            {run ? `Run ${run.id.slice(0, 8)}…` : "Run detail"}
          </SheetTitle>
          <SheetDescription>Ranking run detail</SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          {loading && !run && (
            <div className="text-muted-foreground text-sm py-8">Loading…</div>
          )}
          {run && (
          <>
          <div className="flex flex-wrap gap-2">
            <Badge>{run.status}</Badge>
            <span className="text-muted-foreground text-sm">
              {run.engine_requested ?? "—"} → {run.engine_effective ?? "—"}
            </span>
          </div>
          <div className="grid gap-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">mock_instance_id</span>
              <Button
                variant="ghost"
                size="sm"
                className="font-mono text-xs h-7 px-2"
                onClick={() => copy(run.mock_instance_id)}
              >
                {run.mock_instance_id}
                <Copy className="h-3 w-3 ml-1" />
              </Button>
            </div>
            <div>
              <span className="text-muted-foreground">cohort_id </span>
              <span>{run.cohort_id}</span>
            </div>
            <div>
              <span className="text-muted-foreground">n_users </span>
              <span>{run.n_users ?? "—"}</span>
            </div>
            {run.started_at && (
              <div>
                <span className="text-muted-foreground">started_at </span>
                <span>{new Date(run.started_at).toISOString()}</span>
              </div>
            )}
            {run.finished_at && (
              <div>
                <span className="text-muted-foreground">finished_at </span>
                <span>{new Date(run.finished_at).toISOString()}</span>
              </div>
            )}
          </div>

          {run.parity_report != null && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Parity</span>
                <ParityBadge
                  parityReport={run.parity_report}
                  epsilon={epsilon}
                  compact
                />
              </div>
              <div className="text-xs">
                {(run.parity_report as { max_abs_percentile_diff?: number }).max_abs_percentile_diff != null && (
                  <div>
                    max_abs_percentile_diff:{" "}
                    {(run.parity_report as { max_abs_percentile_diff: number }).max_abs_percentile_diff}
                  </div>
                )}
                {(run.parity_report as { count_mismatch_ranks?: number }).count_mismatch_ranks != null && (
                  <div>
                    count_mismatch_ranks:{" "}
                    {(run.parity_report as { count_mismatch_ranks: number }).count_mismatch_ranks}
                  </div>
                )}
              </div>
              {capped.length > 0 && (
                <div className="space-y-1">
                  <div className="text-sm font-medium">Sample mismatches (cap 20)</div>
                  <pre className="text-xs rounded border bg-muted p-2 overflow-auto max-h-40">
                    {JSON.stringify(capped, null, 2)}
                  </pre>
                </div>
              )}
              <JsonViewer
                data={run.parity_report}
                title="parity_report"
                defaultExpanded={false}
                maxHeight="20rem"
              />
            </div>
          )}

          {run.last_error && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-destructive">last_error</div>
              <pre className="text-xs rounded border border-destructive/50 bg-destructive/5 p-2 overflow-auto max-h-32 whitespace-pre-wrap">
                {run.last_error}
              </pre>
            </div>
          )}

          {!run.parity_report && !run.last_error && (
            <JsonViewer
              data={{
                id: run.id,
                mock_instance_id: run.mock_instance_id,
                cohort_id: run.cohort_id,
                status: run.status,
                engine_requested: run.engine_requested,
                engine_effective: run.engine_effective,
                n_users: run.n_users,
                started_at: run.started_at,
                finished_at: run.finished_at,
                created_at: run.created_at,
              }}
              title="Run metadata"
              defaultExpanded
            />
          )}
          </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
