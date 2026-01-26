/**
 * API client for admin algorithm runtime management.
 */

export type AlgoRuntimeProfile = "V1_PRIMARY" | "V0_FALLBACK";
export type AlgoModule = "mastery" | "revision" | "difficulty" | "adaptive" | "mistakes";
export type AlgoVersion = "v0" | "v1" | "inherit";
// Shadow modules: "irt", "rank", "graph_revision" (handled separately in Learning Ops)

export interface RuntimeConfig {
  active_profile: AlgoRuntimeProfile;
  active_since: string;
  config_json: {
    profile: AlgoRuntimeProfile;
    overrides: Partial<Record<AlgoModule, AlgoVersion>>;
    safe_mode: {
      freeze_updates: boolean;
      prefer_cache: boolean;
    };
  };
}

/** GET /runtime response config shape (uses active_profile). */
export interface RuntimeConfigShape {
  active_profile: AlgoRuntimeProfile;
  overrides: Partial<Record<AlgoModule, AlgoVersion>>;
  safe_mode: {
    freeze_updates: boolean;
    prefer_cache: boolean;
  };
}

export interface SwitchEvent {
  id: string;
  previous_config: {
    active_profile: AlgoRuntimeProfile;
    config_json: RuntimeConfig["config_json"];
    active_since: string;
  };
  new_config: {
    active_profile: AlgoRuntimeProfile;
    config_json: RuntimeConfig["config_json"];
    active_since: string;
  };
  reason: string | null;
  created_at: string;
  created_by: string;
}

export interface BridgeSummary {
  counts_by_status: Record<string, number>;
  total: number;
}

export interface RuntimePayload {
  config: RuntimeConfigShape;
  active_since: string;
  last_switch_events: SwitchEvent[];
  bridge_job_health: BridgeSummary;
}

export interface SwitchRequest {
  profile: AlgoRuntimeProfile;
  overrides?: Partial<Record<AlgoModule, AlgoVersion>>;
  reason: string;
  confirmation_phrase?: string;
  co_approver_code?: string;
}

export interface FreezeRequest {
  reason: string;
  confirmation_phrase?: string;
  co_approver_code?: string;
}

export interface BridgeStatusRow {
  id: string;
  from_profile: AlgoRuntimeProfile;
  to_profile: AlgoRuntimeProfile;
  status: "queued" | "running" | "done" | "failed";
  started_at: string | null;
  finished_at: string | null;
  details: Record<string, unknown> | null;
}

export interface BridgeStatusPayload {
  user_id?: string;
  bridges?: BridgeStatusRow[];
  summary?: BridgeSummary;
}

export const adminAlgorithmsAPI = {
  /**
   * Fetch current runtime configuration and status.
   */
  fetchRuntime: async (): Promise<RuntimePayload> => {
    const response = await fetch("/api/admin/algorithms/runtime", {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load runtime configuration");
    }

    return response.json();
  },

  /**
   * Switch algorithm runtime profile.
   */
  switchRuntime: async (payload: SwitchRequest): Promise<RuntimePayload> => {
    const response = await fetch("/api/admin/algorithms/runtime/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to switch runtime profile");
    }

    return response.json();
  },

  /**
   * Freeze updates (enable safe mode).
   */
  freezeUpdates: async (payload: FreezeRequest): Promise<RuntimePayload> => {
    const response = await fetch("/api/admin/algorithms/runtime/freeze_updates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to freeze updates");
    }

    return response.json();
  },

  /**
   * Unfreeze updates (disable safe mode).
   */
  unfreezeUpdates: async (payload: FreezeRequest): Promise<RuntimePayload> => {
    const response = await fetch("/api/admin/algorithms/runtime/unfreeze_updates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to unfreeze updates");
    }

    return response.json();
  },

  /**
   * Fetch bridge status for a user or overall summary.
   */
  fetchBridgeStatus: async (userId?: string): Promise<BridgeStatusPayload> => {
    const url = userId
      ? `/api/admin/algorithms/bridge/status?user_id=${userId}`
      : "/api/admin/algorithms/bridge/status";

    const response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load bridge status");
    }

    return response.json();
  },
};
