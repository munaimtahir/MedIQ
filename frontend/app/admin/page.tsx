"use client";

import { AdminDashboardHeader } from "@/components/admin/dashboard/AdminDashboardHeader";
import { SyllabusKpiCard } from "@/components/admin/dashboard/SyllabusKpiCard";
import { SystemHealthCard } from "@/components/admin/dashboard/SystemHealthCard";
import { AttentionNeededCard } from "@/components/admin/dashboard/AttentionNeededCard";
import { RecentActivityCard } from "@/components/admin/dashboard/RecentActivityCard";
import { SyllabusShortcutsCard } from "@/components/admin/dashboard/SyllabusShortcutsCard";
import { CsvToolsCard } from "@/components/admin/dashboard/CsvToolsCard";
import { AdminDashboardSkeleton } from "@/components/admin/dashboard/AdminDashboardSkeleton";
import { KpiCard } from "@/components/admin/dashboard/KpiCard";
import { useAdminDashboardSummary, useSystemReady } from "@/lib/admin/dashboard/hooks";
import { useAttentionItems } from "@/lib/admin/dashboard/useAttentionItems";
import { FileQuestion, Upload, Badge } from "lucide-react";

export default function AdminDashboard() {
  const { data: summary, loading: summaryLoading, error: summaryError } = useAdminDashboardSummary();
  const { data: ready, loading: readyLoading } = useSystemReady();
  const { items: attentionItems, loading: attentionLoading } = useAttentionItems();

  const loading = summaryLoading || readyLoading || attentionLoading;

  if (loading && !summary && !ready) {
    return (
      <div className="space-y-6">
        <AdminDashboardSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <AdminDashboardHeader />

      {/* Error Banner */}
      {summaryError && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Failed to load dashboard data: {summaryError.message}
          </p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <SyllabusKpiCard
          years={summary?.syllabus.years ?? null}
          blocks={summary?.syllabus.blocks ?? null}
          themes={summary?.syllabus.themes ?? null}
          loading={summaryLoading}
        />

        <KpiCard
          title="Question Bank"
          value={summary?.content.published ?? null}
          description="Published questions"
          icon={FileQuestion}
          badge={<Badge variant="secondary">Coming soon</Badge>}
          loading={summaryLoading}
        />

        <KpiCard
          title="Imports"
          value={summary?.imports.last_import_at ? "Recent" : null}
          description="Last import activity"
          icon={Upload}
          badge={<Badge variant="secondary">Coming soon</Badge>}
          loading={summaryLoading}
        />

        <SystemHealthCard
          status={ready?.status ?? null}
          checks={ready?.checks}
          loading={readyLoading}
        />
      </div>

      {/* Main Content */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Left Column */}
        <div className="space-y-6">
          <AttentionNeededCard items={attentionItems} loading={attentionLoading} />
          <RecentActivityCard loading={false} />
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          <SyllabusShortcutsCard loading={summaryLoading} />
          <CsvToolsCard loading={false} />
        </div>
      </div>
    </div>
  );
}
