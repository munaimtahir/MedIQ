/**
 * Hooks for runtime control (flags, profile, overrides).
 */

import { useState, useEffect, useCallback } from "react";

export interface RuntimeStatus {
  flags: {
    EXAM_MODE: { enabled: boolean; updated_at: string | null; updated_by: string | { id: string; email: string } | null; reason: string | null; source: string };
    FREEZE_UPDATES: { enabled: boolean; updated_at: string | null; updated_by: string | { id: string; email: string } | null; reason: string | null; source: string };
  };
  active_profile: { name: string; config: Record<string, string>; updated_at: string | null };
  module_overrides: Array<{ module_key: string; version_key: string; is_enabled: boolean; updated_at: string | null }>;
  resolved: {
    profile: string;
    modules: Record<string, string>;
    feature_toggles: Record<string, boolean>;
    freeze_updates: boolean;
    exam_mode: boolean;
    source: Record<string, unknown>;
  };
  last_changed: { action_type: string; created_at: string | null; actor_user_id: string | null } | null;
}

export function useRuntimeStatus() {
  const [status, setStatus] = useState<RuntimeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/runtime/status", {
        method: "GET",
        credentials: "include",
      });
      if (!response.ok) throw new Error("Failed to load runtime status");
      const data: RuntimeStatus = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to load runtime status"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  return { status, loading, error, refetch: loadStatus };
}
