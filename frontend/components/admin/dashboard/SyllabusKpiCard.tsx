"use client";

import { KpiCard } from "./KpiCard";
import { BookOpen } from "lucide-react";
import { useRouter } from "next/navigation";

interface SyllabusKpiCardProps {
  years: number | null;
  blocks: number | null;
  themes: number | null;
  loading?: boolean;
}

export function SyllabusKpiCard({ years, blocks, themes, loading }: SyllabusKpiCardProps) {
  const router = useRouter();

  const total = years !== null && blocks !== null && themes !== null
    ? `${years} years, ${blocks} blocks, ${themes} themes`
    : "--";

  return (
    <KpiCard
      title="Syllabus"
      value={total}
      description="Active curriculum structure"
      icon={BookOpen}
      loading={loading}
      onClick={() => router.push("/admin/syllabus")}
    />
  );
}
