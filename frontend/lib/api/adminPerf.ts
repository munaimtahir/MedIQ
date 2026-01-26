/**
 * Admin Performance API client
 */

import { fetcher } from "@/lib/fetcher";

export interface PerfSummary {
  window: string;
  requests: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  slow_count: number;
  top_routes: Array<{ path: string; count: number; p95_ms: number }>;
  db: { p95_db_ms: number; avg_queries: number };
}

export interface PerfSlowRow {
  request_at: string;
  method: string;
  path: string;
  status_code: number;
  total_ms: number;
  db_total_ms: number;
  db_query_count: number;
  user_role?: string | null;
  request_id?: string | null;
  sampled: boolean;
}

export const adminPerfApi = {
  summary: async (window: string = "24h"): Promise<PerfSummary> => {
    const params = new URLSearchParams();
    params.set("window", window);
    return fetcher<PerfSummary>(`/api/admin/perf/summary?${params.toString()}`);
  },

  slow: async (limit: number = 50): Promise<PerfSlowRow[]> => {
    const params = new URLSearchParams();
    params.set("limit", limit.toString());
    return fetcher<PerfSlowRow[]>(`/api/admin/perf/slow?${params.toString()}`);
  },
};

