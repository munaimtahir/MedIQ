/**
 * Admin Warehouse API client
 */

export interface WarehouseExportRun {
  run_id: string;
  dataset: string;
  run_type: string;
  status: string;
  rows_exported: number;
  files_written: number;
  manifest_path: string | null;
  last_error: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  range_start: string | null;
  range_end: string | null;
}

export interface WarehouseReadinessCheck {
  ok: boolean;
  details: Record<string, unknown>;
}

export interface WarehouseReadiness {
  ready: boolean;
  checks: Record<string, WarehouseReadinessCheck>;
  blocking_reasons: string[];
}

export interface WarehouseRuntimeStatus {
  requested_mode: "disabled" | "shadow" | "active";
  effective_mode: "disabled" | "shadow" | "active";
  warehouse_freeze: boolean;
  readiness: WarehouseReadiness | null;
  last_export_run: {
    run_id: string;
    dataset: string;
    run_type: string;
    status: string;
    finished_at: string | null;
  } | null;
  last_transform_run: unknown | null;
  warnings: string[];
  last_export_runs: Array<{
    run_id: string;
    dataset: string;
    run_type: string;
    status: string;
    rows_exported: number;
    files_written: number;
    created_at: string | null;
  }>;
}

export interface WarehouseSwitchRequest {
  mode: "disabled" | "shadow" | "active";
  reason: string;
  confirmation_phrase: string;
}

export interface ExportRunRequest {
  dataset: string;
  run_type: "incremental" | "backfill" | "full_rebuild";
  range_start?: string | null;
  range_end?: string | null;
  reason: string;
  confirmation_phrase: string;
}

export interface BackfillRequest {
  dataset: string;
  range_start: string;
  range_end: string;
  reason: string;
  confirmation_phrase: string;
}

export interface WarehouseRunsResponse {
  runs: WarehouseExportRun[];
  total: number;
}

export const adminWarehouseAPI = {
  /**
   * Get warehouse runtime status
   */
  getWarehouseRuntime: async (): Promise<WarehouseRuntimeStatus> => {
    const response = await fetch("/api/admin/warehouse/runtime", {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load warehouse runtime");
    }

    return response.json();
  },

  /**
   * Get warehouse readiness status
   */
  getWarehouseReadiness: async (): Promise<WarehouseReadiness> => {
    const response = await fetch("/api/admin/warehouse/runtime", {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load warehouse runtime");
    }

    return response.json();
  },

  /**
   * Switch warehouse mode
   */
  switchWarehouseMode: async (payload: WarehouseSwitchRequest): Promise<WarehouseRuntimeStatus> => {
    const response = await fetch("/api/admin/warehouse/runtime/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to switch warehouse mode");
    }

    return response.json();
  },

  /**
   * Get export runs
   */
  getExportRuns: async (params?: {
    limit?: number;
    dataset?: string;
    status?: string;
  }): Promise<WarehouseRunsResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.dataset) queryParams.append("dataset", params.dataset);
    if (params?.status) queryParams.append("status", params.status);

    const url = `/api/admin/warehouse/runs${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;
    const response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load export runs");
    }

    return response.json();
  },

  /**
   * Run incremental export
   */
  runIncrementalExport: async (payload: {
    reason: string;
    confirmation_phrase: string;
  }): Promise<{ run_ids: string[]; status: string }> => {
    const response = await fetch("/api/admin/warehouse/export/incremental", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to run incremental export");
    }

    const data = await response.json();
    // Backend returns { run_ids: string[], status: string }
    return data;
  },

  /**
   * Run backfill export
   */
  runBackfillExport: async (payload: BackfillRequest): Promise<{ run_id: string }> => {
    const response = await fetch("/api/admin/warehouse/export/backfill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to run backfill export");
    }

    return response.json();
  },
};
