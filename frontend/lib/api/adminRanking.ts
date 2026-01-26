/**
 * Admin Ranking Ops API client (Task 145 – mock exam ranking).
 */

export type RankingMode = "disabled" | "python" | "go_shadow" | "go_active";

export interface RankingReadiness {
  ready: boolean;
  checks: Record<string, { ok: boolean; details?: Record<string, unknown> }>;
  blocking_reasons: string[];
}

export interface RecentParity {
  k: number;
  epsilon?: number;
  pass: boolean;
  max_abs_percentile_diff: number | null;
  rank_mismatch_count: number | null;
  last_checked_at: string | null;
}

export interface RankingRuntimeResponse {
  requested_mode: RankingMode;
  effective_mode: RankingMode;
  freeze: boolean;
  warnings: string[];
  readiness: RankingReadiness | null;
  recent_parity: RecentParity | null;
}

export interface RankingRunListItem {
  id: string;
  mock_instance_id: string;
  cohort_id: string;
  status: string;
  engine_requested: string | null;
  engine_effective: string | null;
  started_at: string | null;
  finished_at: string | null;
  n_users: number | null;
  last_error: string | null;
  parity_report: Record<string, unknown> | null;
  created_at: string;
}

export interface RankingRunsResponse {
  runs: RankingRunListItem[];
}

export interface RankingRunDetail extends RankingRunListItem {}

const BASE = "/api/admin/ranking";

async function getCookieHeaders(): Promise<HeadersInit> {
  return { credentials: "include" } as HeadersInit;
}

async function handleResponse<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (data as { error?: { message?: string } })?.error?.message || "Request failed";
    throw new Error(msg);
  }
  return data as T;
}

export const adminRankingAPI = {
  getRankingRuntime: async (): Promise<RankingRuntimeResponse> => {
    const res = await fetch(`${BASE}/runtime`, {
      method: "GET",
      credentials: "include",
    });
    return handleResponse<RankingRuntimeResponse>(res);
  },

  switchRankingMode: async (
    mode: RankingMode,
    reason: string,
    confirmation_phrase: string
  ): Promise<RankingRuntimeResponse> => {
    const res = await fetch(`${BASE}/runtime/switch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ mode, reason, confirmation_phrase }),
    });
    return handleResponse<RankingRuntimeResponse>(res);
  },

  listRankingRuns: async (params?: { limit?: number }): Promise<RankingRunsResponse> => {
    const q = new URLSearchParams();
    if (params?.limit != null) q.set("limit", String(params.limit));
    const url = `${BASE}/runs${q.toString() ? `?${q.toString()}` : ""}`;
    const res = await fetch(url, { method: "GET", credentials: "include" });
    return handleResponse<RankingRunsResponse>(res);
  },

  getRankingRun: async (id: string): Promise<RankingRunDetail> => {
    const res = await fetch(`${BASE}/runs/${encodeURIComponent(id)}`, {
      method: "GET",
      credentials: "include",
    });
    return handleResponse<RankingRunDetail>(res);
  },

  computeRanking: async (payload: {
    mock_instance_id: string;
    cohort_id: string;
    reason: string;
    confirmation_phrase: string;
    engine_requested?: string | null;
  }): Promise<{ ranking_run_id: string }> => {
    const res = await fetch(`${BASE}/compute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });
    return handleResponse<{ ranking_run_id: string }>(res);
  },
};

/** LOCKED switch phrases (must match backend validation). */
export const RANKING_SWITCH_PHRASES: Record<RankingMode, string> = {
  disabled: "SWITCH RANKING TO DISABLED",
  python: "SWITCH RANKING TO PYTHON",
  go_shadow: "SWITCH RANKING TO GO SHADOW",
  go_active: "SWITCH RANKING TO GO ACTIVE",
};

export const RANKING_COMPUTE_PHRASE = "RUN RANKING COMPUTE";
