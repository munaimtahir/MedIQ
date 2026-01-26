/**
 * Batch apply logic for staged changes.
 * Applies actions in a safe, deterministic order.
 */

import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import type { StagedAction, StagedActionType } from "@/store/changeReviewStore";

export type ApplyProgress = {
  actionId: string;
  status: "pending" | "running" | "success" | "failed" | "skipped";
  error?: string;
  message?: string;
};

export interface ApplyResult {
  succeeded: Array<{ action: StagedAction; progress: ApplyProgress }>;
  failed: Array<{ action: StagedAction; progress: ApplyProgress }>;
  skipped: Array<{ action: StagedAction; progress: ApplyProgress }>;
  rollbackSuggestions: string[];
}

/**
 * Apply staged actions in safe order.
 */
export async function applyChangeBatch(
  stagedActions: StagedAction[],
  reason: string,
  confirmationPhrase: string,
  onProgress?: (progress: ApplyProgress[]) => void,
): Promise<ApplyResult> {
  const result: ApplyResult = {
    succeeded: [],
    failed: [],
    skipped: [],
    rollbackSuggestions: [],
  };

  const progress: ApplyProgress[] = stagedActions.map((action) => ({
    actionId: action.id,
    status: "pending",
  }));

  // PHASE 0: Pre-checks - fetch latest runtime config
  let currentRuntime;
  try {
    currentRuntime = await adminLearningOpsAPI.fetchRuntime();
  } catch (error) {
    // If we can't fetch runtime, mark all as failed
    stagedActions.forEach((action) => {
      const prog = progress.find((p) => p.actionId === action.id)!;
      prog.status = "failed";
      prog.error = "Failed to fetch current runtime state";
    });
    onProgress?.(progress);
    return {
      ...result,
      failed: stagedActions.map((action) => ({
        action,
        progress: progress.find((p) => p.actionId === action.id)!,
      })),
    };
  }

  const isFrozen = currentRuntime.config.safe_mode.freeze_updates;
  const hasWriteActions = stagedActions.some(
    (action) =>
      action.type.includes("ACTIVATE") ||
      action.type.includes("DEACTIVATE") ||
      action.type === "RUNTIME_SWITCH" ||
      action.type === "OVERRIDES_APPLY",
  );

  // Warn if frozen and write actions exist
  if (isFrozen && hasWriteActions) {
    // Still proceed, but mark write actions as potentially blocked
  }

  // PHASE 1: Freeze/Unfreeze
  const freezeActions = stagedActions.filter(
    (action) => action.type === "FREEZE" || action.type === "UNFREEZE",
  );

  for (const action of freezeActions) {
    const prog = progress.find((p) => p.actionId === action.id)!;
    prog.status = "running";
    onProgress?.(progress);

    try {
      if (action.type === "FREEZE") {
        await adminLearningOpsAPI.freezeUpdates({
          reason,
          confirmation_phrase: confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "Freeze applied successfully";
      } else if (action.type === "UNFREEZE") {
        await adminLearningOpsAPI.unfreezeUpdates({
          reason,
          confirmation_phrase: confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "Unfreeze applied successfully";
      }
      result.succeeded.push({ action, progress: prog });
    } catch (error) {
      prog.status = "failed";
      prog.error = error instanceof Error ? error.message : "Unknown error";
      result.failed.push({ action, progress: prog });
      onProgress?.(progress);
      // Stop on first failure
      return result;
    }
    onProgress?.(progress);
  }

  // Re-fetch runtime after freeze/unfreeze to get updated state
  try {
    currentRuntime = await adminLearningOpsAPI.fetchRuntime();
  } catch {
    // Continue even if refetch fails
  }

  const isFrozenAfterPhase1 = currentRuntime.config.safe_mode.freeze_updates;

  // PHASE 2: Runtime switch + overrides
  const runtimeActions = stagedActions.filter(
    (action) => action.type === "RUNTIME_SWITCH" || action.type === "OVERRIDES_APPLY",
  );

  for (const action of runtimeActions) {
    const prog = progress.find((p) => p.actionId === action.id)!;
    prog.status = "running";
    onProgress?.(progress);

    try {
      if (action.type === "RUNTIME_SWITCH") {
        const payload = action.payload as {
          profile: "V1_PRIMARY" | "V0_FALLBACK";
          overrides?: Record<string, "v0" | "v1">;
        };
        await adminLearningOpsAPI.switchRuntime({
          profile: payload.profile,
          overrides: payload.overrides,
          reason,
          confirmation_phrase: confirmationPhrase,
        });
        prog.status = "success";
        prog.message = `Runtime switched to ${payload.profile}`;
      } else if (action.type === "OVERRIDES_APPLY") {
        // Overrides are typically included in runtime switch, but handle separately if needed
        const payload = action.payload as {
          profile: "V1_PRIMARY" | "V0_FALLBACK";
          overrides: Record<string, "v0" | "v1">;
        };
        await adminLearningOpsAPI.switchRuntime({
          profile: payload.profile,
          overrides: payload.overrides,
          reason,
          confirmation_phrase: confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "Overrides applied successfully";
      }
      result.succeeded.push({ action, progress: prog });
    } catch (error) {
      prog.status = "failed";
      prog.error = error instanceof Error ? error.message : "Unknown error";
      result.failed.push({ action, progress: prog });
      onProgress?.(progress);
      return result;
    }
    onProgress?.(progress);
  }

  // PHASE 3: Subsystem activations (only if not frozen)
  const activationActions = stagedActions.filter(
    (action) =>
      action.type.includes("ACTIVATE") || action.type.includes("DEACTIVATE"),
  );

  for (const action of activationActions) {
    const prog = progress.find((p) => p.actionId === action.id)!;

    // Skip if frozen
    if (isFrozenAfterPhase1) {
      prog.status = "skipped";
      prog.message = "Skipped: freeze_updates is enabled";
      result.skipped.push({ action, progress: prog });
      onProgress?.(progress);
      continue;
    }

    prog.status = "running";
    onProgress?.(progress);

    try {
      if (action.type === "IRT_ACTIVATE") {
        const payload = action.payload as {
          run_id: string;
          scope: string;
          model_type: string;
        };
        await adminLearningOpsAPI.activateIrt({
          ...payload,
          reason,
          confirmation_phrase: action.requiredPhrase || confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "IRT activated successfully";
      } else if (action.type === "IRT_DEACTIVATE") {
        await adminLearningOpsAPI.deactivateIrt({
          reason,
          confirmation_phrase: action.requiredPhrase || confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "IRT deactivated successfully";
      } else if (action.type === "RANK_ACTIVATE") {
        const payload = action.payload as { cohort_key: string };
        await adminLearningOpsAPI.activateRank({
          ...payload,
          reason,
          confirmation_phrase: action.requiredPhrase || confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "Rank activated successfully";
      } else if (action.type === "RANK_DEACTIVATE") {
        await adminLearningOpsAPI.deactivateRank({
          reason,
          confirmation_phrase: action.requiredPhrase || confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "Rank deactivated successfully";
      } else if (action.type === "GRAPH_ACTIVATE") {
        await adminLearningOpsAPI.activateGraph({
          reason,
          confirmation_phrase: action.requiredPhrase || confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "Graph revision activated successfully";
      } else if (action.type === "GRAPH_DEACTIVATE") {
        await adminLearningOpsAPI.deactivateGraph({
          reason,
          confirmation_phrase: action.requiredPhrase || confirmationPhrase,
        });
        prog.status = "success";
        prog.message = "Graph revision deactivated successfully";
      }
      result.succeeded.push({ action, progress: prog });
    } catch (error) {
      prog.status = "failed";
      prog.error = error instanceof Error ? error.message : "Unknown error";
      result.failed.push({ action, progress: prog });
      onProgress?.(progress);
      return result;
    }
    onProgress?.(progress);
  }

  // Generate rollback suggestions
  if (result.failed.length > 0 || result.skipped.length > 0) {
    const runtimeSwitched = result.succeeded.some(
      (item) => item.action.type === "RUNTIME_SWITCH",
    );
    const activationsFailed = result.failed.some(
      (item) => item.action.type.includes("ACTIVATE") || item.action.type.includes("DEACTIVATE"),
    );

    if (runtimeSwitched && activationsFailed) {
      result.rollbackSuggestions.push(
        "Consider switching runtime profile back to previous state if activations are critical.",
      );
    }

    if (result.skipped.length > 0) {
      result.rollbackSuggestions.push(
        "Some actions were skipped due to freeze mode. Unfreeze and re-apply if needed.",
      );
    }
  }

  return result;
}
