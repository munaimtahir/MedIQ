/**
 * Hooks for admin dashboard data fetching.
 */

import { useEffect, useState } from "react";

interface DashboardSummary {
  syllabus: {
    years: number;
    blocks: number;
    themes: number;
  };
  content: {
    published: number | null;
    in_review: number | null;
    draft: number | null;
  };
  imports: {
    last_import_at: string | null;
    failed_rows: number | null;
  };
}

interface SystemReady {
  status: "ok" | "degraded" | "down";
  checks: Record<string, { status: "ok" | "degraded" | "down"; message?: string | null }>;
  request_id: string;
}

interface UseDashboardSummaryResult {
  data: DashboardSummary | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

interface UseSystemReadyResult {
  data: SystemReady | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Fetch admin dashboard summary.
 */
export function useAdminDashboardSummary(): UseDashboardSummaryResult {
  const [state, setState] = useState<UseDashboardSummaryResult>({
    data: null,
    loading: true,
    error: null,
    refetch: () => {},
  });

  const loadSummary = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await fetch("/api/admin/dashboard/summary", {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData?.error?.message || "Failed to load dashboard summary";
        throw new Error(errorMessage);
      }

      const data: DashboardSummary = await response.json();
      setState({
        data,
        loading: false,
        error: null,
        refetch: loadSummary,
      });
    } catch (error) {
      setState({
        data: null,
        loading: false,
        error: error instanceof Error ? error : new Error("Failed to load dashboard summary"),
        refetch: loadSummary,
      });
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  return state;
}

/**
 * Fetch system readiness status.
 */
export function useSystemReady(): UseSystemReadyResult {
  const [state, setState] = useState<UseSystemReadyResult>({
    data: null,
    loading: true,
    error: null,
    refetch: () => {},
  });

  const loadReady = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await fetch("/api/admin/system/ready", {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to check system readiness");
      }

      const data: SystemReady = await response.json();
      setState({
        data,
        loading: false,
        error: null,
        refetch: loadReady,
      });
    } catch (error) {
      setState({
        data: null,
        loading: false,
        error: error instanceof Error ? error : new Error("Failed to check system readiness"),
        refetch: loadReady,
      });
    }
  };

  useEffect(() => {
    loadReady();
  }, []);

  return state;
}
