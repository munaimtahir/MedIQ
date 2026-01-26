import { create } from "zustand";

export type StagedActionType =
  | "RUNTIME_SWITCH"
  | "OVERRIDES_APPLY"
  | "FREEZE"
  | "UNFREEZE"
  | "IRT_ACTIVATE"
  | "IRT_DEACTIVATE"
  | "RANK_ACTIVATE"
  | "RANK_DEACTIVATE"
  | "GRAPH_ACTIVATE"
  | "GRAPH_DEACTIVATE";

export type RiskLevel = "high" | "medium" | "low";

export interface StagedAction {
  id: string;
  type: StagedActionType;
  payload: unknown;
  diffSummary: string;
  riskLevel: RiskLevel;
  requiredPhrase: string; // Per-action phrase for backend
}

interface ChangeReviewState {
  stagedActions: StagedAction[];
  addAction: (action: Omit<StagedAction, "id">) => void;
  removeAction: (id: string) => void;
  clearAll: () => void;
  hasChanges: () => boolean;
}

// Generate unique ID for staged action
function generateActionId(): string {
  return `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Get conflict groups - actions that should replace each other
function getConflictGroup(type: StagedActionType): string {
  if (type === "FREEZE" || type === "UNFREEZE") return "freeze_group";
  if (type === "IRT_ACTIVATE" || type === "IRT_DEACTIVATE") return "irt_group";
  if (type === "RANK_ACTIVATE" || type === "RANK_DEACTIVATE") return "rank_group";
  if (type === "GRAPH_ACTIVATE" || type === "GRAPH_DEACTIVATE") return "graph_group";
  if (type === "RUNTIME_SWITCH") return "runtime_switch_group";
  if (type === "OVERRIDES_APPLY") return "overrides_group";
  return "none";
}

export const useChangeReviewStore = create<ChangeReviewState>((set, get) => ({
  stagedActions: [],

  addAction: (action) => {
    const conflictGroup = getConflictGroup(action.type);
    const existingActions = get().stagedActions;

    // Remove conflicting actions
    const filteredActions = existingActions.filter(
      (existing) => getConflictGroup(existing.type) !== conflictGroup,
    );

    // Add new action
    const newAction: StagedAction = {
      ...action,
      id: generateActionId(),
    };

    set({ stagedActions: [...filteredActions, newAction] });
  },

  removeAction: (id) => {
    set({
      stagedActions: get().stagedActions.filter((action) => action.id !== id),
    });
  },

  clearAll: () => {
    set({ stagedActions: [] });
  },

  hasChanges: () => {
    return get().stagedActions.length > 0;
  },
}));
