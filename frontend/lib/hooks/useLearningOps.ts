/**
 * React hooks for Learning Ops dashboard.
 */

import { useState, useCallback, useEffect } from "react";
import { notify } from "@/lib/notify";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import type {
  RuntimeStatus,
  IrtStatus,
  RankStatus,
  GraphHealth,
  IrtRun,
  SwitchRuntimeRequest,
  FreezeRequest,
  SearchRuntimeStatus,
} from "@/lib/api/adminLearningOps";

// Runtime
export function useRuntime() {
  const [data, setData] = useState<RuntimeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchRuntime = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminLearningOpsAPI.fetchRuntime();
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load runtime configuration");
      setError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuntime();
    const interval = setInterval(fetchRuntime, 30000); // Refetch every 30 seconds
    return () => clearInterval(interval);
  }, [fetchRuntime]);

  return { data, loading, error, refetch: fetchRuntime };
}

// IRT
export function useIrtStatus() {
  const [data, setData] = useState<IrtStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminLearningOpsAPI.fetchIrtStatus();
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load IRT status");
      setError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { data, loading, error, refetch: fetchStatus };
}

export function useIrtRuns() {
  const [data, setData] = useState<IrtRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminLearningOpsAPI.fetchIrtRuns({ limit: 1 });
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load IRT runs");
      setError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 30000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  return { data, loading, error, refetch: fetchRuns };
}

// Rank
export function useRankStatus(cohortKey: string) {
  const [data, setData] = useState<RankStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminLearningOpsAPI.fetchRankStatus(cohortKey);
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load Rank status");
      setError(error);
    } finally {
      setLoading(false);
    }
  }, [cohortKey]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { data, loading, error, refetch: fetchStatus };
}

// Graph Revision
export function useGraphHealth() {
  const [data, setData] = useState<GraphHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminLearningOpsAPI.fetchGraphHealth();
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load Graph health");
      setError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return { data, loading, error, refetch: fetchHealth };
}

// Search Runtime
export function useSearchRuntime() {
  const [data, setData] = useState<SearchRuntimeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminLearningOpsAPI.fetchSearchRuntime();
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load Search runtime status");
      setError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { data, loading, error, refetch: fetchStatus };
}
