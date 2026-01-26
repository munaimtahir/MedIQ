/**
 * API client for Admin Learning Ops dashboard.
 * Unified control plane for runtime + IRT + Rank + Graph Revision.
 */

// ============================================================================
// Runtime API
// ============================================================================

export interface RuntimeStatus {
  config: {
    active_profile: "V1_PRIMARY" | "V0_FALLBACK";
    overrides: Record<string, "v0" | "v1" | "shadow">;
    safe_mode: {
      freeze_updates: boolean;
      prefer_cache: boolean;
    };
  };
  active_since: string;
  last_switch_events: Array<{
    id: string;
    previous_config: {
      active_profile: string;
      config_json: {
        profile: string;
        overrides: Record<string, string>;
        safe_mode: { freeze_updates: boolean; prefer_cache: boolean };
      };
      active_since: string;
    };
    new_config: {
      active_profile: string;
      config_json: {
        profile: string;
        overrides: Record<string, string>;
        safe_mode: { freeze_updates: boolean; prefer_cache: boolean };
      };
      active_since: string;
    };
    reason: string | null;
    created_at: string;
    created_by: string;
  }>;
  bridge_job_health: {
    counts_by_status: Record<string, number>;
    total: number;
  };
}

export interface SwitchRuntimeRequest {
  profile: "V1_PRIMARY" | "V0_FALLBACK";
  overrides?: Record<string, "v0" | "v1">;
  reason: string;
  confirmation_phrase: string;
  co_approver_code?: string;
}

export interface FreezeRequest {
  reason: string;
  confirmation_phrase: string;
  co_approver_code?: string;
}

export interface BridgeStatusRequest {
  user_id?: string;
}

export interface BridgeStatusResponse {
  user_id?: string;
  bridges?: Array<{
    id: string;
    from_profile: string;
    to_profile: string;
    status: "queued" | "running" | "done" | "failed";
    started_at: string | null;
    finished_at: string | null;
    details: Record<string, unknown> | null;
  }>;
  summary?: {
    counts_by_status: Record<string, number>;
    total: number;
  };
}

// ============================================================================
// IRT API
// ============================================================================

export interface IrtStatus {
  flags: {
    active: boolean;
    scope: string;
    model: string;
    shadow: boolean;
  };
  latest_decision: {
    eligible: boolean;
    run_id: string | null;
    created_at: string | null;
  };
  last_events: Array<{
    event_type: string;
    created_at: string;
    reason: string | null;
    created_by_user_id: string;
  }>;
}

export interface IrtRun {
  id: string;
  model_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  metrics: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
}

export interface IrtRunCreate {
  model_type: "IRT_2PL" | "IRT_3PL";
  dataset_spec: Record<string, unknown>;
  seed?: number;
  notes?: string;
}

export interface IrtEligibilityEvaluate {
  run_id: string;
  policy_version?: string;
}

export interface IrtActivate {
  run_id: string;
  scope: string;
  model_type: string;
  reason: string;
  confirmation_phrase: string;
}

export interface IrtDeactivate {
  reason: string;
  confirmation_phrase: string;
}

// ============================================================================
// Rank API
// ============================================================================

export interface RankStatus {
  mode: "v0" | "shadow" | "v1";
  latest_run: {
    id: string | null;
    status: string | null;
    coverage: number | null;
    stability: number | null;
    created_at: string | null;
  } | null;
  eligible: boolean;
  reasons: string[];
}

export interface RankRun {
  id: string;
  cohort_key: string;
  model_version: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  metrics: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
}

export interface RankRunCreate {
  cohort_key: string;
  dataset_spec?: Record<string, unknown>;
  notes?: string;
}

export interface RankActivate {
  cohort_key: string;
  reason: string;
  confirmation_phrase: string;
  force?: boolean;
}

export interface RankDeactivate {
  reason: string;
  confirmation_phrase: string;
}

// ============================================================================
// Graph Revision API
// ============================================================================

export interface GraphHealth {
  neo4j_available: boolean;
  graph_stats: {
    available: boolean;
    node_count: number;
    edge_count: number;
    error?: string;
  };
  cycle_check: {
    has_cycles: boolean;
    cycles: unknown[];
    cycle_count: number;
    error?: string;
  };
  last_sync: {
    id: string | null;
    status: string | null;
    finished_at: string | null;
    details: Record<string, unknown> | null;
  } | null;
}

export interface GraphSyncRun {
  id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  details_json: Record<string, unknown> | null;
  created_at: string;
}

export interface GraphRunMetrics {
  runs: Array<{
    id: string;
    run_date: string;
    mode: string;
    metrics: Record<string, unknown> | null;
    status: string;
    created_at: string;
  }>;
}

export interface GraphActivate {
  reason: string;
  confirmation_phrase: string;
  force?: boolean;
}

export interface GraphDeactivate {
  reason: string;
  confirmation_phrase: string;
}

// ============================================================================
// API Client
// ============================================================================

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(endpoint, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error?.message || errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Search Runtime API
// ============================================================================

export interface ReadinessCheckDetails {
  ok: boolean;
  details: Record<string, unknown>;
}

export interface ReadinessStatus {
  ready: boolean;
  blocking_reasons: string[];
  checks: Record<string, ReadinessCheckDetails>;
}

export interface SearchRuntimeStatus {
  requested_mode: "postgres" | "elasticsearch";
  effective_engine: "postgres" | "elasticsearch";
  enabled: boolean;
  es_reachable: boolean;
  last_switch: {
    at: string;
    by: string;
    reason: string;
  } | null;
  readiness: ReadinessStatus | null;
}

export interface SearchSwitchRequest {
  mode: "postgres" | "elasticsearch";
  reason: string;
  confirmation_phrase: string;
}

export const adminLearningOpsAPI = {
  // Runtime
  fetchRuntime: async (): Promise<RuntimeStatus> => {
    return apiRequest<RuntimeStatus>("/api/admin/algorithms/runtime");
  },

  switchRuntime: async (payload: SwitchRuntimeRequest): Promise<RuntimeStatus> => {
    return apiRequest<RuntimeStatus>("/api/admin/algorithms/runtime/switch", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  freezeUpdates: async (payload: FreezeRequest): Promise<RuntimeStatus> => {
    return apiRequest<RuntimeStatus>("/api/admin/algorithms/runtime/freeze_updates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  unfreezeUpdates: async (payload: FreezeRequest): Promise<RuntimeStatus> => {
    return apiRequest<RuntimeStatus>("/api/admin/algorithms/runtime/unfreeze_updates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  fetchBridgeStatus: async (params?: BridgeStatusRequest): Promise<BridgeStatusResponse> => {
    const query = params?.user_id ? `?user_id=${encodeURIComponent(params.user_id)}` : "";
    return apiRequest<BridgeStatusResponse>(`/api/admin/algorithms/bridge/status${query}`);
  },

  // IRT
  fetchIrtStatus: async (): Promise<IrtStatus> => {
    const response = await apiRequest<{
      flags: {
        active: boolean;
        scope: string;
        model: string;
        shadow: boolean;
      };
      latest_decision: {
        eligible: boolean | null;
        run_id: string | null;
        created_at: string | null;
      };
      recent_events: Array<{
        event_type: string;
        created_at: string;
        created_by: string;
        reason: string | null;
      }>;
    }>("/api/admin/irt/activation/status");
    // Transform to match IrtStatus interface
    return {
      flags: response.flags,
      latest_decision: {
        eligible: response.latest_decision.eligible ?? false,
        run_id: response.latest_decision.run_id,
        created_at: response.latest_decision.created_at,
      },
      last_events: response.recent_events.map((e) => ({
        event_type: e.event_type,
        created_at: e.created_at,
        reason: e.reason,
        created_by_user_id: e.created_by,
      })),
    };
  },

  fetchIrtRuns: async (params?: { status?: string; model_type?: string; limit?: number }): Promise<IrtRun[]> => {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append("status", params.status);
    if (params?.model_type) queryParams.append("model_type", params.model_type);
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
    return apiRequest<IrtRun[]>(`/api/admin/irt/runs${query}`);
  },

  createIrtRun: async (payload: IrtRunCreate): Promise<IrtRun> => {
    return apiRequest<IrtRun>("/api/admin/irt/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  evaluateIrtEligibility: async (payload: IrtEligibilityEvaluate): Promise<{
    eligible: boolean;
    gates: Array<{
      name: string;
      passed: boolean;
      value: unknown;
      threshold: unknown;
      notes?: string;
    }>;
    recommended_scope: string;
    recommended_model: string;
  }> => {
    const response = await apiRequest<{
      decision: {
        eligible: boolean;
        policy_version: string;
        evaluated_at: string;
        recommended_scope: string;
        recommended_model: string;
      };
      eligible: boolean;
      gates: Array<{
        name: string;
        passed: boolean;
        value: number | null;
        threshold: number | null;
        notes: string;
      }>;
    }>("/api/admin/irt/activation/evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return {
      eligible: response.eligible,
      gates: response.gates,
      recommended_scope: response.decision.recommended_scope,
      recommended_model: response.decision.recommended_model,
    };
  },

  activateIrt: async (payload: IrtActivate): Promise<{ message: string }> => {
    return apiRequest("/api/admin/irt/activation/activate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  deactivateIrt: async (payload: IrtDeactivate): Promise<{ message: string }> => {
    return apiRequest("/api/admin/irt/activation/deactivate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Rank
  fetchRankStatus: async (cohortKey?: string): Promise<RankStatus> => {
    const query = cohortKey ? `?cohort_key=${encodeURIComponent(cohortKey)}` : "";
    return apiRequest<RankStatus>(`/api/admin/rank/status${query}`);
  },

  fetchRankRuns: async (params?: { cohort_key?: string; status?: string; limit?: number }): Promise<RankRun[]> => {
    const queryParams = new URLSearchParams();
    if (params?.cohort_key) queryParams.append("cohort_key", params.cohort_key);
    if (params?.status) queryParams.append("status", params.status);
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
    return apiRequest<RankRun[]>(`/api/admin/rank/runs${query}`);
  },

  createRankRun: async (payload: RankRunCreate): Promise<RankRun> => {
    return apiRequest<RankRun>("/api/admin/rank/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  activateRank: async (payload: RankActivate): Promise<{ message: string }> => {
    return apiRequest("/api/admin/rank/activate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  deactivateRank: async (payload: RankDeactivate): Promise<{ message: string }> => {
    return apiRequest("/api/admin/rank/deactivate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Graph Revision
  fetchGraphHealth: async (): Promise<GraphHealth> => {
    return apiRequest<GraphHealth>("/api/admin/graph-revision/health");
  },

  fetchGraphRunMetrics: async (days?: number): Promise<GraphRunMetrics> => {
    const query = days ? `?days=${days}` : "";
    return apiRequest<GraphRunMetrics>(`/api/admin/graph-revision/run-metrics${query}`);
  },

  fetchGraphSyncRuns: async (limit?: number): Promise<GraphSyncRun[]> => {
    const query = limit ? `?limit=${limit}` : "";
    return apiRequest<GraphSyncRun[]>(`/api/admin/graph-revision/sync/runs${query}`);
  },

  runGraphSync: async (): Promise<GraphSyncRun> => {
    return apiRequest<GraphSyncRun>("/api/admin/graph-revision/sync", {
      method: "POST",
    });
  },

  activateGraph: async (payload: GraphActivate): Promise<{ message: string; eligible: boolean; reasons: string[] }> => {
    return apiRequest("/api/admin/graph-revision/activate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  deactivateGraph: async (payload: GraphDeactivate): Promise<{ message: string }> => {
    return apiRequest("/api/admin/graph-revision/deactivate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Search Runtime
  fetchSearchRuntime: async (): Promise<SearchRuntimeStatus> => {
    return apiRequest<SearchRuntimeStatus>("/api/admin/search/runtime");
  },

  switchSearchRuntime: async (payload: SearchSwitchRequest): Promise<{ message: string; previous_mode: string; new_mode: string; warnings?: string[] }> => {
    return apiRequest<{ message: string; previous_mode: string; new_mode: string; warnings?: string[] }>("/api/admin/search/runtime/switch", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
