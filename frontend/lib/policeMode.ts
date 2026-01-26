/**
 * Police Mode utilities for typed confirmation safeguards.
 */

export type ActionType = "PROFILE_SWITCH" | "FREEZE" | "UNFREEZE" | "OVERRIDES_APPLY";

export interface ConfirmationConfig {
  actionType: ActionType;
  targetProfile?: "V1_PRIMARY" | "V0_FALLBACK";
  caseSensitive?: boolean;
}

/**
 * Get the required confirmation phrase for an action.
 */
export function getRequiredPhrase(config: ConfirmationConfig): string {
  switch (config.actionType) {
    case "PROFILE_SWITCH":
      if (config.targetProfile === "V1_PRIMARY") {
        return "SWITCH TO V1_PRIMARY";
      } else if (config.targetProfile === "V0_FALLBACK") {
        return "SWITCH TO V0_FALLBACK";
      }
      throw new Error("PROFILE_SWITCH requires targetProfile");
    case "FREEZE":
      return "FREEZE UPDATES";
    case "UNFREEZE":
      return "UNFREEZE UPDATES";
    case "OVERRIDES_APPLY":
      return "APPLY OVERRIDES";
    default:
      throw new Error(`Unknown action type: ${config.actionType}`);
  }
}

/**
 * Check if the input phrase matches the required phrase.
 */
export function isPhraseMatch(
  input: string,
  required: string,
  mode: "exact" | "case-insensitive" = "case-insensitive",
): boolean {
  if (mode === "case-insensitive") {
    return input.trim().toUpperCase() === required.toUpperCase();
  }
  return input.trim() === required;
}

/**
 * Get risk summary checklist items.
 */
export function getRiskChecklist(): Array<{ label: string; checked: boolean }> {
  return [
    { label: "Applies to new sessions only (session snapshot rule)", checked: true },
    { label: "Existing sessions unaffected", checked: true },
    { label: "Bridge is lazy per-user (no reset)", checked: true },
    { label: "Rollback available via toggle", checked: true },
  ];
}
