/**
 * Helper functions to stage actions for batch review.
 */

import { useChangeReviewStore, type StagedActionType, type RiskLevel } from "@/store/changeReviewStore";
import type { AlgoRuntimeProfile, AlgoModule, AlgoVersion } from "@/lib/admin/algorithms/api";

export function stageRuntimeSwitch(
  profile: AlgoRuntimeProfile,
  overrides: Partial<Record<AlgoModule, AlgoVersion>>,
  currentProfile: AlgoRuntimeProfile,
  currentOverrides: Partial<Record<AlgoModule, AlgoVersion>>,
): void {
  const store = useChangeReviewStore.getState();
  const cleanOverrides: Record<string, "v0" | "v1"> = {};
  Object.entries(overrides).forEach(([key, value]) => {
    if (value && value !== "inherit") {
      cleanOverrides[key] = value as "v0" | "v1";
    }
  });

  const hasProfileChange = profile !== currentProfile;
  const hasOverrideChanges = JSON.stringify(cleanOverrides) !== JSON.stringify(currentOverrides || {});

  if (hasProfileChange) {
    store.addAction({
      type: "RUNTIME_SWITCH",
      payload: {
        profile,
        overrides: Object.keys(cleanOverrides).length > 0 ? cleanOverrides : undefined,
      },
      diffSummary: `Switch runtime profile from ${currentProfile} to ${profile}`,
      riskLevel: "high",
      requiredPhrase: profile === "V1_PRIMARY" ? "SWITCH TO V1_PRIMARY" : "SWITCH TO V0_FALLBACK",
    });
  }

  if (hasOverrideChanges && !hasProfileChange) {
    store.addAction({
      type: "OVERRIDES_APPLY",
      payload: {
        profile: currentProfile,
        overrides: cleanOverrides,
      },
      diffSummary: `Apply module overrides: ${Object.keys(cleanOverrides).join(", ")}`,
      riskLevel: "medium",
      requiredPhrase: "APPLY OVERRIDES",
    });
  }
}

export function stageFreeze(isCurrentlyFrozen: boolean): void {
  const store = useChangeReviewStore.getState();
  store.addAction({
    type: isCurrentlyFrozen ? "UNFREEZE" : "FREEZE",
    payload: {},
    diffSummary: isCurrentlyFrozen ? "Unfreeze updates (enable writes)" : "Freeze updates (disable writes)",
    riskLevel: "high",
    requiredPhrase: isCurrentlyFrozen ? "UNFREEZE UPDATES" : "FREEZE UPDATES",
  });
}

export function stageIrtActivate(
  runId: string,
  scope: string,
  modelType: string,
): void {
  const store = useChangeReviewStore.getState();
  store.addAction({
    type: "IRT_ACTIVATE",
    payload: {
      run_id: runId,
      scope,
      model_type: modelType,
    },
    diffSummary: `Activate IRT with model ${modelType} (scope: ${scope})`,
    riskLevel: "high",
    requiredPhrase: "ACTIVATE IRT",
  });
}

export function stageIrtDeactivate(): void {
  const store = useChangeReviewStore.getState();
  store.addAction({
    type: "IRT_DEACTIVATE",
    payload: {},
    diffSummary: "Deactivate IRT (return to shadow mode)",
    riskLevel: "medium",
    requiredPhrase: "DEACTIVATE IRT",
  });
}

export function stageRankActivate(cohortKey: string): void {
  const store = useChangeReviewStore.getState();
  store.addAction({
    type: "RANK_ACTIVATE",
    payload: {
      cohort_key: cohortKey,
    },
    diffSummary: `Activate Rank for cohort ${cohortKey}`,
    riskLevel: "high",
    requiredPhrase: "ACTIVATE RANK",
  });
}

export function stageRankDeactivate(): void {
  const store = useChangeReviewStore.getState();
  store.addAction({
    type: "RANK_DEACTIVATE",
    payload: {},
    diffSummary: "Deactivate Rank (return to shadow mode)",
    riskLevel: "medium",
    requiredPhrase: "DEACTIVATE RANK",
  });
}

export function stageGraphActivate(): void {
  const store = useChangeReviewStore.getState();
  store.addAction({
    type: "GRAPH_ACTIVATE",
    payload: {},
    diffSummary: "Activate Graph Revision",
    riskLevel: "high",
    requiredPhrase: "ACTIVATE GRAPH REVISION",
  });
}

export function stageGraphDeactivate(): void {
  const store = useChangeReviewStore.getState();
  store.addAction({
    type: "GRAPH_DEACTIVATE",
    payload: {},
    diffSummary: "Deactivate Graph Revision (return to shadow mode)",
    riskLevel: "medium",
    requiredPhrase: "DEACTIVATE GRAPH REVISION",
  });
}
