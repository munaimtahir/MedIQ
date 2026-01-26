/**
 * React hooks for algorithm runtime management.
 */

import { useState, useCallback, useEffect } from "react";
import { notify } from "@/lib/notify";
import {
  adminAlgorithmsAPI,
  type RuntimePayload,
  type SwitchRequest,
  type FreezeRequest,
  type BridgeStatusPayload,
} from "./api";

export function useAlgorithmRuntime() {
  const [data, setData] = useState<RuntimePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchRuntime = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminAlgorithmsAPI.fetchRuntime();
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load runtime configuration");
      setError(error);
      notify.error("Failed to load runtime", error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuntime();
  }, [fetchRuntime]);

  const switchRuntime = useCallback(
    async (payload: SwitchRequest) => {
      try {
        const result = await adminAlgorithmsAPI.switchRuntime(payload);
        setData(result);
        notify.success("Runtime switched", "Algorithm profile updated successfully");
        return result;
      } catch (err: any) {
        // Check if approval is required (409 error)
        if (err?.response?.status === 409 || err?.message?.includes("APPROVAL_REQUIRED")) {
          // Automatically create approval request
          try {
            const { requestApproval } = await import("@/lib/admin/approvals/api");
            const actionType =
              payload.profile === "V1_PRIMARY" ? "PROFILE_SWITCH_PRIMARY" : "PROFILE_SWITCH_FALLBACK";
            const confirmationPhrase =
              payload.profile === "V1_PRIMARY"
                ? "SWITCH TO V1_PRIMARY"
                : "SWITCH TO V0_FALLBACK";

            await requestApproval({
              action_type: actionType as any,
              action_payload: {
                profile: payload.profile,
                overrides: payload.overrides || {},
              },
              reason: payload.reason,
              confirmation_phrase: confirmationPhrase,
            });

            notify.info(
              "Approval Required",
              "Approval request created. Waiting for second admin approval.",
            );
            // Refetch to show pending approval
            await fetchRuntime();
            return;
          } catch (approvalErr) {
            const error = approvalErr instanceof Error ? approvalErr : new Error("Failed to request approval");
            notify.error("Approval request failed", error.message);
            throw error;
          }
        }

        const error = err instanceof Error ? err : new Error("Failed to switch runtime");
        notify.error("Switch failed", error.message);
        throw error;
      }
    },
    [fetchRuntime],
  );

  const freezeUpdates = useCallback(
    async (payload: FreezeRequest) => {
      try {
        const result = await adminAlgorithmsAPI.freezeUpdates(payload);
        setData(result);
        notify.success("Updates frozen", "System is now in read-only mode");
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to freeze updates");
        notify.error("Freeze failed", error.message);
        throw error;
      }
    },
    [],
  );

  const unfreezeUpdates = useCallback(
    async (payload: FreezeRequest) => {
      try {
        const result = await adminAlgorithmsAPI.unfreezeUpdates(payload);
        setData(result);
        notify.success("Updates unfrozen", "System is now in normal mode");
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to unfreeze updates");
        notify.error("Unfreeze failed", error.message);
        throw error;
      }
    },
    [],
  );

  return {
    data,
    loading,
    error,
    refetch: fetchRuntime,
    switchRuntime,
    freezeUpdates,
    unfreezeUpdates,
  };
}

export function useBridgeStatus(userId?: string) {
  const [data, setData] = useState<BridgeStatusPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!userId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await adminAlgorithmsAPI.fetchBridgeStatus(userId);
      setData(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load bridge status");
      setError(error);
      notify.error("Failed to load bridge status", error.message);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  return {
    data,
    loading,
    error,
    refetch: fetchStatus,
  };
}
