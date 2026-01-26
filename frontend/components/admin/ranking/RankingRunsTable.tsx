"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ParityBadge } from "./ParityBadge";
import type { RankingRunListItem } from "@/lib/api/adminRanking";
import { notify } from "@/lib/notify";
import { formatDistanceToNow } from "date-fns";
import { Copy, Eye } from "lucide-react";

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  done: "default",
  running: "secondary",
  queued: "outline",
  failed: "destructive",
};

interface RankingRunsTableProps {
  runs: RankingRunListItem[];
  loading: boolean;
  epsilon?: number | null;
  onViewRun: (run: RankingRunListItem) => void;
}

function copyId(text: string) {
  navigator.clipboard.writeText(text);
  notify.success("Copied", "ID copied to clipboard");
}

export function RankingRunsTable({
  runs,
  loading,
  epsilon,
  onViewRun,
}: RankingRunsTableProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Runs</CardTitle>
        <CardDescription>Ranking run history</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-muted-foreground text-sm py-8 text-center">Loading…</div>
        ) : runs.length === 0 ? (
          <div className="text-muted-foreground text-sm py-8 text-center">No runs yet</div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Started</TableHead>
                  <TableHead>mock_instance_id</TableHead>
                  <TableHead>cohort_id</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Requested / Effective</TableHead>
                  <TableHead>n_users</TableHead>
                  <TableHead>Parity</TableHead>
                  <TableHead>Δ% / Mismatches</TableHead>
                  <TableHead>last_error</TableHead>
                  <TableHead className="w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                      {r.started_at
                        ? formatDistanceToNow(new Date(r.started_at), { addSuffix: true })
                        : "—"}
                    </TableCell>
                    <TableCell>
                      <button
                        type="button"
                        onClick={() => copyId(r.mock_instance_id)}
                        className="font-mono text-xs hover:underline flex items-center gap-1"
                        title="Copy"
                      >
                        {r.mock_instance_id.slice(0, 8)}…
                        <Copy className="h-3 w-3" />
                      </button>
                    </TableCell>
                    <TableCell className="text-xs">{r.cohort_id}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANTS[r.status] ?? "outline"}>{r.status}</Badge>
                    </TableCell>
                    <TableCell className="text-xs">
                      {r.engine_requested ?? "—"} / {r.engine_effective ?? "—"}
                    </TableCell>
                    <TableCell>{r.n_users ?? "—"}</TableCell>
                    <TableCell>
                      {r.parity_report != null ? (
                        <ParityBadge
                          parityReport={r.parity_report}
                          epsilon={epsilon}
                          compact
                        />
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs">
                      {r.parity_report != null ? (
                        (() => {
                          const pr = r.parity_report as {
                            max_abs_percentile_diff?: number | null;
                            count_mismatch_ranks?: number | null;
                          };
                          const d = pr.max_abs_percentile_diff;
                          const m = pr.count_mismatch_ranks;
                          if (d == null && m == null) return "—";
                          const parts: string[] = [];
                          if (d != null) parts.push(`${d.toFixed(6)}`);
                          if (m != null) parts.push(`${m} misc`);
                          return parts.join(" / ");
                        })()
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="max-w-[120px] truncate text-xs text-muted-foreground" title={r.last_error ?? ""}>
                      {r.last_error ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" onClick={() => onViewRun(r)} className="gap-1">
                        <Eye className="h-3 w-3" />
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
