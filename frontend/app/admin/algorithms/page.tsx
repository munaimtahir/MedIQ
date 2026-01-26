"use client";

import { useAlgorithmRuntime } from "@/lib/admin/algorithms/hooks";
import type { AlgoModule, AlgoVersion } from "@/lib/admin/algorithms/api";
import { RuntimeControlsCard } from "@/components/admin/algorithms/RuntimeControlsCard";
import { SafeModeCard } from "@/components/admin/algorithms/SafeModeCard";
import { HealthCard } from "@/components/admin/algorithms/HealthCard";
import { SwitchAuditTable } from "@/components/admin/algorithms/SwitchAuditTable";
import { PendingApprovalsCard } from "@/components/admin/approvals/PendingApprovalsCard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Info } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";

export default function AlgorithmsPage() {
  const {
    data,
    loading,
    error,
    refetch,
    switchRuntime,
    freezeUpdates,
    unfreezeUpdates,
  } = useAlgorithmRuntime();

  const handleSwitch = async (
    profile: "V1_PRIMARY" | "V0_FALLBACK",
    overrides: Partial<Record<AlgoModule, AlgoVersion>>,
    reason: string,
    confirmationPhrase?: string,
    coApproverCode?: string,
  ) => {
    await switchRuntime({
      profile,
      overrides,
      reason,
      confirmation_phrase: confirmationPhrase,
      co_approver_code: coApproverCode,
    });
    await refetch();
  };

  const handleFreeze = async (
    reason: string,
    confirmationPhrase?: string,
    coApproverCode?: string,
  ) => {
    await freezeUpdates({
      reason,
      confirmation_phrase: confirmationPhrase,
      co_approver_code: coApproverCode,
    });
    await refetch();
  };

  const handleUnfreeze = async (
    reason: string,
    confirmationPhrase?: string,
    coApproverCode?: string,
  ) => {
    await unfreezeUpdates({
      reason,
      confirmation_phrase: confirmationPhrase,
      co_approver_code: coApproverCode,
    });
    await refetch();
  };

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-muted animate-pulse rounded" />
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-64 bg-muted animate-pulse rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Algorithm Runtime</h1>
        <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
          <span>
            Profile:{" "}
            <Badge variant={data?.config.active_profile === "V1_PRIMARY" ? "default" : "secondary"}>
              {data?.config.active_profile || "Loading..."}
            </Badge>
          </span>
          {data?.active_since && (
            <span>
              Active since: {formatDistanceToNow(new Date(data.active_since), { addSuffix: true })}
            </span>
          )}
          {data?.config.safe_mode.freeze_updates && (
            <Badge variant="destructive">Updates Frozen</Badge>
          )}
        </div>
      </div>

      {/* Pending Approvals Banner */}
      <PendingApprovalsCard />

      {/* Session Snapshot Rule Callout */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          <strong>Session Snapshot Rule:</strong> Changes apply to <strong>new sessions only</strong>.
          In-progress sessions retain their starting profile and will not be affected by runtime
          switches.
        </AlertDescription>
      </Alert>

      {/* Error Banner */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load runtime configuration: {error.message}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div className="md:col-span-2">
          <RuntimeControlsCard
            data={data}
            loading={loading}
            onSwitch={handleSwitch}
          />
        </div>
        <div>
          <SafeModeCard
            data={data}
            loading={loading}
            onFreeze={handleFreeze}
            onUnfreeze={handleUnfreeze}
          />
        </div>
        <div className="md:col-span-3">
          <HealthCard bridgeSummary={data?.bridge_job_health || null} />
        </div>
      </div>

      {/* Audit Trail */}
      <SwitchAuditTable events={data?.last_switch_events || []} loading={loading} />
    </div>
  );
}
