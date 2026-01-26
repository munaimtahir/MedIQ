"use client";

import { useState, useEffect, useCallback } from "react";
import { WarehouseStatusCard } from "@/components/admin/warehouse/WarehouseStatusCard";
import { ExportControlsCard } from "@/components/admin/warehouse/ExportControlsCard";
import { ExportRunsTable } from "@/components/admin/warehouse/ExportRunsTable";
import { adminWarehouseAPI, type WarehouseRuntimeStatus, type WarehouseExportRun } from "@/lib/api/adminWarehouse";
import { notify } from "@/lib/notify";

export default function WarehousePage() {
  const [runtime, setRuntime] = useState<WarehouseRuntimeStatus | null>(null);
  const [runs, setRuns] = useState<WarehouseExportRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [runsLoading, setRunsLoading] = useState(false);
  const [filters, setFilters] = useState<{ status?: string; dataset?: string }>({});

  const fetchRuntime = useCallback(async () => {
    try {
      const data = await adminWarehouseAPI.getWarehouseRuntime();
      setRuntime(data);
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to load warehouse status", err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRuns = useCallback(async () => {
    setRunsLoading(true);
    try {
      const data = await adminWarehouseAPI.getExportRuns({
        limit: 50,
        ...filters,
      });
      setRuns(data.runs);
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to load export runs", err.message);
    } finally {
      setRunsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchRuntime();
    fetchRuns();
  }, [fetchRuntime, fetchRuns]);

  // Auto-refresh runs every 30 seconds when on page
  useEffect(() => {
    const interval = setInterval(() => {
      fetchRuns();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  // Refetch runtime on window focus
  useEffect(() => {
    const handleFocus = () => {
      fetchRuntime();
    };
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [fetchRuntime]);

  const handleSwitchMode = async (
    mode: "disabled" | "shadow" | "active",
    reason: string,
    phrase: string
  ) => {
    try {
      const data = await adminWarehouseAPI.switchWarehouseMode({ mode, reason, confirmation_phrase: phrase });
      setRuntime(data);
      notify.success("Mode switched", `Warehouse mode changed to ${mode}`);
      await fetchRuns(); // Refresh runs
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to switch mode", err.message);
      throw error;
    }
  };

  const handleRunIncremental = async (reason: string, phrase: string) => {
    try {
      const result = await adminWarehouseAPI.runIncrementalExport({ reason, confirmation_phrase: phrase });
      notify.success("Export started", `Incremental export queued: ${result.run_ids.length} run(s)`);
      await fetchRuns(); // Refresh runs
      await fetchRuntime(); // Refresh runtime
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to run export", err.message);
      throw error;
    }
  };

  const handleRunBackfill = async (
    dataset: string,
    rangeStart: string,
    rangeEnd: string,
    reason: string,
    phrase: string
  ) => {
    try {
      await adminWarehouseAPI.runBackfillExport({
        dataset,
        range_start: rangeStart,
        range_end: rangeEnd,
        reason,
        confirmation_phrase: phrase,
      });
      notify.success("Backfill started", "Backfill export has been queued");
      await fetchRuns(); // Refresh runs
      await fetchRuntime(); // Refresh runtime
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to run backfill", err.message);
      throw error;
    }
  };

  const handleFilterChange = useCallback((newFilters: { status?: string; dataset?: string }) => {
    setFilters(newFilters);
  }, []);

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Warehouse Export</h1>
        <p className="text-muted-foreground">
          Manage Snowflake export pipeline (currently files-only, no Snowflake loading)
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <WarehouseStatusCard data={runtime} loading={loading} onSwitchMode={handleSwitchMode} />
        <ExportControlsCard
          data={runtime}
          loading={loading}
          onRunIncremental={handleRunIncremental}
          onRunBackfill={handleRunBackfill}
        />
      </div>

      <ExportRunsTable runs={runs} loading={runsLoading} onFilterChange={handleFilterChange} />
    </div>
  );
}
