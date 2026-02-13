"use client";

import { useState, useMemo } from "react";
import { LearningOpsHeader } from "@/components/admin/learningOps/LearningOpsHeader";
import { RuntimeControlsCard } from "@/components/admin/algorithms/RuntimeControlsCard";
import { SafeModeCard } from "@/components/admin/algorithms/SafeModeCard";
import { ShadowSystemsGrid } from "@/components/admin/learningOps/ShadowSystemsGrid";
import { AuditTrailTabs } from "@/components/admin/learningOps/AuditTrailTabs";
import { BridgeLookupPanel } from "@/components/admin/learningOps/BridgeLookupPanel";
import { ChangeReviewDrawer } from "@/components/admin/learningOps/ChangeReviewDrawer";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Info, FileText } from "lucide-react";
import { useChangeReviewStore } from "@/store/changeReviewStore";
import { useRuntime, useIrtStatus, useIrtRuns, useRankStatus, useGraphHealth, useSearchRuntime } from "@/lib/hooks/useLearningOps";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { notify } from "@/lib/notify";
import type {
  AlgoModule,
  AlgoVersion,
  AlgoRuntimeProfile,
  RuntimePayload,
  SwitchEvent,
} from "@/lib/admin/algorithms/api";

export default function LearningOpsPage() {
  const [rankCohortKey, setRankCohortKey] = useState("year:1");
  const [showChangeReview, setShowChangeReview] = useState(false);
  const hasStagedChanges = useChangeReviewStore((state) => state.hasChanges());
  const stagedCount = useChangeReviewStore((state) => state.stagedActions.length);

  // Data fetching
  const runtimeQuery = useRuntime();
  const irtStatusQuery = useIrtStatus();
  const irtRunsQuery = useIrtRuns();
  const rankStatusQuery = useRankStatus(rankCohortKey);
  const graphHealthQuery = useGraphHealth();
  const searchRuntimeQuery = useSearchRuntime();

  // Compute "Safe to Activate" status
  const safeToActivate = useMemo<"safe" | "caution" | "unsafe">(() => {
    const runtime = runtimeQuery.data;
    const irtStatus = irtStatusQuery.data;
    const rankStatus = rankStatusQuery.data;
    const graphHealth = graphHealthQuery.data;

    if (!runtime) return "unsafe";

    // Unsafe if frozen
    if (runtime.config.safe_mode.freeze_updates) {
      return "unsafe";
    }

    // Check each subsystem
    const irtOk = irtStatus?.latest_decision.eligible || irtStatus?.flags.active || false;
    const rankOk = rankStatus?.eligible || rankStatus?.mode === "v1" || false;
    const graphOk =
      (graphHealth?.neo4j_available && !graphHealth?.cycle_check.has_cycles) ||
      false; // TODO: Get actual graph mode from runtime

    // Unsafe if critical infra down while active
    if ((irtStatus?.flags.active || rankStatus?.mode === "v1") && !graphHealth?.neo4j_available) {
      return "unsafe";
    }

    // Caution if some subsystems not eligible but inactive
    if (!irtOk || !rankOk || !graphOk) {
      return "caution";
    }

    return "safe";
  }, [runtimeQuery.data, irtStatusQuery.data, rankStatusQuery.data, graphHealthQuery.data]);

  const handleSwitch = async (
    profile: "V1_PRIMARY" | "V0_FALLBACK",
    overrides: Partial<Record<AlgoModule, AlgoVersion>>,
    reason: string,
    confirmationPhrase?: string,
  ) => {
    try {
      // Filter out "inherit" and convert to Record<string, "v0" | "v1">
      const cleanOverrides: Record<string, "v0" | "v1"> = {};
      Object.entries(overrides).forEach(([key, value]) => {
        if (value && value !== "inherit") {
          cleanOverrides[key] = value as "v0" | "v1";
        }
      });
      await adminLearningOpsAPI.switchRuntime({
        profile,
        overrides: Object.keys(cleanOverrides).length > 0 ? cleanOverrides : undefined,
        reason,
        confirmation_phrase: confirmationPhrase || "",
      });
      notify.success("Runtime switched", "Algorithm profile updated successfully");
      await runtimeQuery.refetch();
    } catch (error) {
      notify.error("Switch failed", error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleFreeze = async (reason: string, confirmationPhrase?: string) => {
    try {
      await adminLearningOpsAPI.freezeUpdates({
        reason,
        confirmation_phrase: confirmationPhrase || "",
      });
      notify.success("Updates frozen", "System is now in read-only mode");
      await runtimeQuery.refetch();
    } catch (error) {
      notify.error("Freeze failed", error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleUnfreeze = async (reason: string, confirmationPhrase?: string) => {
    try {
      await adminLearningOpsAPI.unfreezeUpdates({
        reason,
        confirmation_phrase: confirmationPhrase || "",
      });
      notify.success("Updates unfrozen", "System is now in normal mode");
      await runtimeQuery.refetch();
    } catch (error) {
      notify.error("Unfreeze failed", error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleRefresh = async () => {
    await Promise.all([
      runtimeQuery.refetch(),
      irtStatusQuery.refetch(),
      irtRunsQuery.refetch(),
      rankStatusQuery.refetch(),
      graphHealthQuery.refetch(),
      searchRuntimeQuery.refetch(),
    ]);
  };

  const loading =
    runtimeQuery.loading ||
    irtStatusQuery.loading ||
    irtRunsQuery.loading ||
    rankStatusQuery.loading ||
    graphHealthQuery.loading ||
    searchRuntimeQuery.loading;

  const error =
    runtimeQuery.error || irtStatusQuery.error || irtRunsQuery.error || rankStatusQuery.error || graphHealthQuery.error || searchRuntimeQuery.error;

  return (
    <div className="space-y-6">
      {/* Header */}
      <LearningOpsHeader
        runtime={runtimeQuery.data || null}
        safeToActivate={safeToActivate}
        loading={loading}
      />

      {/* Session Snapshot Rule Callout */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          <strong>Session Snapshot Rule:</strong> Changes apply to <strong>new sessions only</strong>.
          In-progress sessions retain their starting profile and will not be affected by runtime switches.
        </AlertDescription>
      </Alert>

      {/* Shadow Mode Callout */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          <strong>Shadow Mode:</strong> Shadow systems (IRT, Rank, Graph Revision) compute metrics and plans
          but do not affect student-facing decisions unless explicitly activated.
        </AlertDescription>
      </Alert>

      {/* Freeze Mode Callout */}
      {runtimeQuery.data?.config.safe_mode.freeze_updates && (
        <Alert variant="warning">
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>Freeze Updates:</strong> All learning state writes are paused. Students can still practice,
            but mastery/revision updates will not change until unfrozen.
          </AlertDescription>
        </Alert>
      )}

      {/* Error Banner */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load data: {error instanceof Error ? error.message : "Unknown error"}
          </AlertDescription>
        </Alert>
      )}

      {/* Section A: Runtime Control */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div className="md:col-span-2">
          <RuntimeControlsCard
            data={
              runtimeQuery.data
                ? {
                    config: {
                      active_profile: runtimeQuery.data.config.active_profile as "V1_PRIMARY" | "V0_FALLBACK",
                      overrides: runtimeQuery.data.config.overrides as Partial<
                        Record<"mastery" | "revision" | "difficulty" | "adaptive" | "mistakes", "v0" | "v1">
                      >,
                      safe_mode: runtimeQuery.data.config.safe_mode,
                    },
                    active_since: runtimeQuery.data.active_since,
                    last_switch_events: runtimeQuery.data.last_switch_events.map((e) => {
                      const prev = e.previous_config as {
                        active_profile?: string;
                        config_json?: {
                          profile?: string;
                          overrides?: Record<string, string>;
                          safe_mode?: { freeze_updates?: boolean; prefer_cache?: boolean };
                        };
                        active_since?: string;
                      };
                      const next = e.new_config as {
                        active_profile?: string;
                        config_json?: {
                          profile?: string;
                          overrides?: Record<string, string>;
                          safe_mode?: { freeze_updates?: boolean; prefer_cache?: boolean };
                        };
                        active_since?: string;
                      };
                      return {
                        id: e.id,
                        previous_config: {
                          active_profile: (prev?.active_profile as AlgoRuntimeProfile) || "V1_PRIMARY",
                          config_json: prev?.config_json || {
                            profile: "V1_PRIMARY",
                            overrides: {},
                            safe_mode: { freeze_updates: false, prefer_cache: true },
                          },
                          active_since: prev?.active_since || "",
                        },
                        new_config: {
                          active_profile: (next?.active_profile as AlgoRuntimeProfile) || "V1_PRIMARY",
                          config_json: next?.config_json || {
                            profile: "V1_PRIMARY",
                            overrides: {},
                            safe_mode: { freeze_updates: false, prefer_cache: true },
                          },
                          active_since: next?.active_since || "",
                        },
                        reason: e.reason,
                        created_at: e.created_at,
                        created_by: e.created_by,
                      } as SwitchEvent;
                    }),
                    bridge_job_health: runtimeQuery.data.bridge_job_health,
                  }
                : null
            }
            loading={loading}
            onSwitch={handleSwitch}
          />
        </div>
        <div>
          <SafeModeCard
            data={
              runtimeQuery.data
                ? {
                    config: {
                      active_profile: runtimeQuery.data.config.active_profile as "V1_PRIMARY" | "V0_FALLBACK",
                      overrides: runtimeQuery.data.config.overrides as Partial<
                        Record<"mastery" | "revision" | "difficulty" | "adaptive" | "mistakes", "v0" | "v1">
                      >,
                      safe_mode: runtimeQuery.data.config.safe_mode,
                    },
                    active_since: runtimeQuery.data.active_since,
                    last_switch_events: [],
                    bridge_job_health: runtimeQuery.data.bridge_job_health,
                  }
                : null
            }
            loading={loading}
            onFreeze={handleFreeze}
            onUnfreeze={handleUnfreeze}
          />
        </div>
      </div>

      {/* Section B: Shadow Systems Status Grid */}
      <div>
        <h2 className="mb-4 text-2xl font-semibold">Shadow Systems</h2>
        <ShadowSystemsGrid
          runtime={runtimeQuery.data || null}
          irtStatus={irtStatusQuery.data || null}
          irtLastRun={irtRunsQuery.data?.[0] || null}
          rankStatus={rankStatusQuery.data || null}
          rankCohortKey={rankCohortKey}
          onRankCohortKeyChange={setRankCohortKey}
          graphHealth={graphHealthQuery.data || null}
          searchRuntime={searchRuntimeQuery.data || null}
          loading={loading}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Section C: Unified Audit Trail */}
      <div>
        <h2 className="mb-4 text-2xl font-semibold">Audit Trail</h2>
        <AuditTrailTabs runtime={runtimeQuery.data || null} loading={loading} />
      </div>

      {/* Section D: Drilldown Tools */}
      <div>
        <h2 className="mb-4 text-2xl font-semibold">Drilldown Tools</h2>
        <BridgeLookupPanel />
      </div>

      {/* Change Review Drawer */}
      <ChangeReviewDrawer
        open={showChangeReview}
        onOpenChange={setShowChangeReview}
        onApplyComplete={handleRefresh}
      />

      {/* Review Changes Button - Floating */}
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          onClick={() => setShowChangeReview(true)}
          size="lg"
          className="shadow-lg"
          variant={hasStagedChanges ? "default" : "outline"}
        >
          <FileText className="mr-2 h-5 w-5" />
          Review changes
          {hasStagedChanges && (
            <Badge variant="secondary" className="ml-2">
              {stagedCount}
            </Badge>
          )}
        </Button>
      </div>
    </div>
  );
}
