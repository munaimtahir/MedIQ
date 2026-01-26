"use client";

import { IrtOpsCard } from "./IrtOpsCard";
import { RankOpsCard } from "./RankOpsCard";
import { GraphOpsCard } from "./GraphOpsCard";
import { SearchOpsCard } from "./SearchOpsCard";
import type {
  RuntimeStatus,
  IrtStatus,
  RankStatus,
  GraphHealth,
  IrtRun,
  SearchRuntimeStatus,
} from "@/lib/api/adminLearningOps";

interface ShadowSystemsGridProps {
  runtime: RuntimeStatus | null;
  irtStatus: IrtStatus | null;
  irtLastRun: IrtRun | null;
  rankStatus: RankStatus | null;
  rankCohortKey: string;
  onRankCohortKeyChange: (key: string) => void;
  graphHealth: GraphHealth | null;
  searchRuntime: SearchRuntimeStatus | null;
  loading?: boolean;
  onRefresh: () => void;
}

export function ShadowSystemsGrid({
  runtime,
  irtStatus,
  irtLastRun,
  rankStatus,
  rankCohortKey,
  onRankCohortKeyChange,
  graphHealth,
  searchRuntime,
  loading,
  onRefresh,
}: ShadowSystemsGridProps) {
  const isFrozen = runtime?.config.safe_mode.freeze_updates || false;

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      <IrtOpsCard
        status={irtStatus}
        lastRun={irtLastRun}
        isFrozen={isFrozen}
        loading={loading}
        onRefresh={onRefresh}
      />
      <RankOpsCard
        status={rankStatus}
        cohortKey={rankCohortKey}
        onCohortKeyChange={onRankCohortKeyChange}
        isFrozen={isFrozen}
        loading={loading}
        onRefresh={onRefresh}
      />
      <GraphOpsCard
        health={graphHealth}
        runtime={runtime}
        isFrozen={isFrozen}
        loading={loading}
        onRefresh={onRefresh}
      />
      <SearchOpsCard
        status={searchRuntime}
        isFrozen={isFrozen}
        loading={loading}
        onRefresh={onRefresh}
      />
    </div>
  );
}
