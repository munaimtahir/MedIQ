"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import { ParityBadge } from "./ParityBadge";
import {
  RANKING_SWITCH_PHRASES,
  type RankingMode,
  type RankingRuntimeResponse,
} from "@/lib/api/adminRanking";
import { AlertTriangle, Cpu } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface RankingStatusCardProps {
  data: RankingRuntimeResponse | null;
  loading: boolean;
  onSwitchMode: (mode: RankingMode, reason: string, phrase: string) => Promise<void>;
}

export function RankingStatusCard({ data, loading, onSwitchMode }: RankingStatusCardProps) {
  const [switchMode, setSwitchMode] = useState<RankingMode | null>(null);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const requested = (data?.requested_mode ?? "python") as RankingMode;
  const effective = (data?.effective_mode ?? "python") as RankingMode;
  const isFrozen = data?.freeze ?? false;
  const readiness = data?.readiness;
  const isReady = readiness?.ready ?? false;
  const recentParity = data?.recent_parity;
  const parityPass = recentParity?.pass ?? true;

  const canGoActive = !isFrozen && isReady && parityPass;

  const handleSwitch = async () => {
    if (!switchMode) return;
    setIsSubmitting(true);
    try {
      await onSwitchMode(switchMode, reason, RANKING_SWITCH_PHRASES[switchMode]);
      setSwitchMode(null);
      setReason("");
    } catch {
      // parent handles toast
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Ranking Status
          </CardTitle>
          <CardDescription>Mock exam ranking engine (Python baseline, Go shadow/active)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Requested:</span>
              <Badge variant="outline">{requested}</Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Effective:</span>
              <Badge
                variant={
                  effective === "go_active"
                    ? "default"
                    : effective === "go_shadow"
                      ? "secondary"
                      : "outline"
                }
              >
                {effective}
              </Badge>
            </div>
            {isFrozen && (
              <Badge variant="destructive">Frozen</Badge>
            )}
            {readiness && (
              <Badge variant={readiness.ready ? "default" : "destructive"}>
                {readiness.ready ? "READY" : "NOT READY"}
              </Badge>
            )}
          </div>

          {readiness && !readiness.ready && readiness.blocking_reasons.length > 0 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-1">
                  <div className="font-medium">Blocking reasons</div>
                  <ul className="list-inside list-disc space-y-1 text-sm">
                    {readiness.blocking_reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {data?.warnings && data.warnings.length > 0 && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                {data.warnings.join("; ")}
              </AlertDescription>
            </Alert>
          )}

          {recentParity && (
            <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Recent parity</span>
                <ParityBadge
                  parityReport={{
                    max_abs_percentile_diff: recentParity.max_abs_percentile_diff,
                    count_mismatch_ranks: recentParity.rank_mismatch_count,
                  }}
                  epsilon={recentParity.epsilon}
                  compact
                />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span>K={recentParity.k}</span>
                {recentParity.max_abs_percentile_diff != null && (
                  <span>max Δ% = {recentParity.max_abs_percentile_diff.toFixed(6)}</span>
                )}
                {recentParity.rank_mismatch_count != null && (
                  <span>rank mismatches = {recentParity.rank_mismatch_count}</span>
                )}
                {recentParity.last_checked_at && (
                  <span>last checked {formatDistanceToNow(new Date(recentParity.last_checked_at))} ago</span>
                )}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              variant={requested === "disabled" ? "default" : "outline"}
              size="sm"
              onClick={() => setSwitchMode("disabled")}
              disabled={loading || isFrozen}
            >
              Disabled
            </Button>
            <Button
              variant={requested === "python" ? "default" : "outline"}
              size="sm"
              onClick={() => setSwitchMode("python")}
              disabled={loading || isFrozen}
            >
              Python (default)
            </Button>
            <Button
              variant={requested === "go_shadow" ? "default" : "outline"}
              size="sm"
              onClick={() => setSwitchMode("go_shadow")}
              disabled={loading || isFrozen}
            >
              Go Shadow
            </Button>
            <Button
              variant={requested === "go_active" ? "default" : "outline"}
              size="sm"
              onClick={() => setSwitchMode("go_active")}
              disabled={loading || isFrozen || !canGoActive}
              title={
                !canGoActive && readiness?.blocking_reasons?.length
                  ? `Blocked: ${readiness.blocking_reasons.join("; ")}`
                  : !parityPass
                    ? "Parity failed; fix recent parity before Go Active"
                    : undefined
              }
            >
              Go Active
            </Button>
          </div>
          {isFrozen && (
            <p className="text-xs text-muted-foreground">Ranking is frozen. Unfreeze to change mode.</p>
          )}
        </CardContent>
      </Card>

      {switchMode && (
        <PoliceConfirmModal
          open
          onOpenChange={(open) => !open && setSwitchMode(null)}
          actionTitle={`Switch Ranking to ${switchMode === "go_active" ? "Go Active" : switchMode === "go_shadow" ? "Go Shadow" : switchMode.toUpperCase()}`}
          requiredPhrase={RANKING_SWITCH_PHRASES[switchMode]}
          reason={reason}
          onReasonChange={setReason}
          onConfirm={handleSwitch}
          isSubmitting={isSubmitting}
          variant={switchMode === "disabled" ? "destructive" : "default"}
        />
      )}
    </>
  );
}
