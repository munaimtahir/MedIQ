"use client";

import { useState, useCallback, useEffect } from "react";
import { RankingStatusCard } from "@/components/admin/ranking/RankingStatusCard";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { ComputeCard } from "@/components/admin/ranking/ComputeCard";
import { RankingRunsTable } from "@/components/admin/ranking/RankingRunsTable";
import { RunDetailDrawer } from "@/components/admin/ranking/RunDetailDrawer";
import {
  adminRankingAPI,
  type RankingRuntimeResponse,
  type RankingRunListItem,
} from "@/lib/api/adminRanking";
import { notify } from "@/lib/notify";

export default function RankingOpsPage() {
  const [runtime, setRuntime] = useState<RankingRuntimeResponse | null>(null);
  const [runs, setRuns] = useState<RankingRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RankingRunListItem | null>(null);
  const [runDetail, setRunDetail] = useState<RankingRunListItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchRuntime = useCallback(async () => {
    setRuntimeError(null);
    try {
      const data = await adminRankingAPI.getRankingRuntime();
      setRuntime(data);
    } catch (e) {
      const err = e instanceof Error ? e : new Error("Failed to load ranking runtime");
      setRuntimeError(err.message);
      notify.error("Runtime error", err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRuns = useCallback(async () => {
    setRunsLoading(true);
    try {
      const data = await adminRankingAPI.listRankingRuns({ limit: 50 });
      setRuns(data.runs);
    } catch (e) {
      const err = e instanceof Error ? e : new Error("Failed to load runs");
      notify.error("Runs error", err.message);
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuntime();
    fetchRuns();
  }, [fetchRuntime, fetchRuns]);

  useEffect(() => {
    const t = setInterval(fetchRuns, 45_000);
    return () => clearInterval(t);
  }, [fetchRuns]);

  useEffect(() => {
    const onFocus = () => fetchRuntime();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [fetchRuntime]);

  const handleSwitch = async (
    mode: "disabled" | "python" | "go_shadow" | "go_active",
    reason: string,
    phrase: string
  ) => {
    const data = await adminRankingAPI.switchRankingMode(mode, reason, phrase);
    setRuntime(data);
    notify.success("Mode switched", `Ranking mode set to ${mode}`);
    await fetchRuns();
  };

  const handleCompute = async (payload: {
    mock_instance_id: string;
    cohort_id: string;
    reason: string;
    confirmation_phrase: string;
  }) => {
    const res = await adminRankingAPI.computeRanking(payload);
    notify.success("Compute started", `Run ${res.ranking_run_id}`);
    await fetchRuns();
    await fetchRuntime();
  };

  const handleViewRun = useCallback(
    async (run: RankingRunListItem) => {
      setSelectedRun(run);
      setDrawerOpen(true);
      setDetailLoading(true);
      setRunDetail(null);
      try {
        const detail = await adminRankingAPI.getRankingRun(run.id);
        setRunDetail(detail);
      } catch (e) {
        notify.error("Run detail", e instanceof Error ? e.message : "Failed to load");
        setRunDetail(run);
      } finally {
        setDetailLoading(false);
      }
    },
    []
  );

  const epsilon = runtime?.recent_parity?.epsilon ?? 0.001;

  return (
    <div className="container mx-auto space-y-6 py-6">
      <div>
        <h1 className="text-3xl font-bold">Ranking Ops</h1>
        <p className="text-muted-foreground">
          Mock exam ranking (Python baseline, Go shadow/active). Admin-only; does not affect students.
        </p>
      </div>

      {runtimeError && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between gap-4">
            <span>{runtimeError}</span>
            <Button variant="outline" size="sm" onClick={() => { setLoading(true); fetchRuntime(); }}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <RankingStatusCard
          data={runtime}
          loading={loading}
          onSwitchMode={handleSwitch}
        />
        <ComputeCard
          data={runtime}
          loading={loading}
          onCompute={handleCompute}
        />
      </div>

      <RankingRunsTable
        runs={runs}
        loading={runsLoading}
        epsilon={epsilon}
        onViewRun={handleViewRun}
      />

      <RunDetailDrawer
        run={runDetail ?? selectedRun}
        open={drawerOpen}
        onOpenChange={(open) => {
          setDrawerOpen(open);
          if (!open) {
            setSelectedRun(null);
            setRunDetail(null);
          }
        }}
        epsilon={epsilon}
        loading={detailLoading}
      />
    </div>
  );
}
