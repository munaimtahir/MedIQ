"use client";

import { KpiCard } from "./KpiCard";
import { Activity } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface SystemHealthCardProps {
  status: "ok" | "degraded" | "down" | null;
  checks?: Record<string, { status: "ok" | "degraded" | "down"; message?: string | null }>;
  loading?: boolean;
}

export function SystemHealthCard({ status, checks, loading }: SystemHealthCardProps) {
  const getStatusBadge = () => {
    if (!status) return null;

    const variants = {
      ok: "default",
      degraded: "secondary",
      down: "destructive",
    } as const;

    const labels = {
      ok: "Healthy",
      degraded: "Degraded",
      down: "Down",
    } as const;

    return (
      <Badge variant={variants[status]}>
        {labels[status]}
      </Badge>
    );
  };

  const getStatusValue = () => {
    if (!status) return "--";
    if (status === "ok") return "All systems operational";
    if (status === "degraded") return "Some services degraded";
    return "System unavailable";
  };

  const getDescription = () => {
    if (!checks) return "System status";
    
    const dbStatus = checks.db?.status || "unknown";
    const redisStatus = checks.redis?.status || "unknown";
    
    return `DB: ${dbStatus}, Redis: ${redisStatus}`;
  };

  return (
    <KpiCard
      title="System Health"
      value={getStatusValue()}
      description={getDescription()}
      icon={Activity}
      badge={getStatusBadge()}
      loading={loading}
    />
  );
}
