"use client";

import { useState } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Copy, ChevronDown, ChevronUp } from "lucide-react";
import { notify } from "@/lib/notify";
import { formatDistanceToNow } from "date-fns";
import type { WarehouseExportRun } from "@/lib/api/adminWarehouse";

interface ExportRunsTableProps {
  runs: WarehouseExportRun[];
  loading: boolean;
  onFilterChange: (filters: { status?: string; dataset?: string }) => void;
}

const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  shadow_done_files_only: "default",
  done: "default",
  running: "secondary",
  queued: "outline",
  failed: "destructive",
  blocked_disabled: "destructive",
  blocked_frozen: "destructive",
};

export function ExportRunsTable({ runs, loading, onFilterChange }: ExportRunsTableProps) {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [datasetFilter, setDatasetFilter] = useState<string>("");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    onFilterChange({ status: value || undefined, dataset: datasetFilter || undefined });
  };

  const handleDatasetFilter = (value: string) => {
    setDatasetFilter(value);
    onFilterChange({ status: statusFilter || undefined, dataset: value || undefined });
  };

  const toggleRow = (runId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(runId)) {
      newExpanded.delete(runId);
    } else {
      newExpanded.add(runId);
    }
    setExpandedRows(newExpanded);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    notify.success("Copied", "Path copied to clipboard");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Export Runs</CardTitle>
        <CardDescription>History of warehouse export runs</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="flex gap-4">
          <div className="space-y-2 flex-1">
            <Label htmlFor="status-filter">Status</Label>
            <Select value={statusFilter} onValueChange={handleStatusFilter}>
              <SelectTrigger id="status-filter">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All statuses</SelectItem>
                <SelectItem value="shadow_done_files_only">Shadow Done</SelectItem>
                <SelectItem value="done">Done</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="queued">Queued</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="blocked_disabled">Blocked (Disabled)</SelectItem>
                <SelectItem value="blocked_frozen">Blocked (Frozen)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 flex-1">
            <Label htmlFor="dataset-filter">Dataset</Label>
            <Select value={datasetFilter} onValueChange={handleDatasetFilter}>
              <SelectTrigger id="dataset-filter">
                <SelectValue placeholder="All datasets" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All datasets</SelectItem>
                <SelectItem value="attempts">Attempts</SelectItem>
                <SelectItem value="events">Events</SelectItem>
                <SelectItem value="mastery">Mastery</SelectItem>
                <SelectItem value="revision_queue">Revision Queue</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">Loading...</div>
        ) : runs.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">No export runs found</div>
        ) : (
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Started</TableHead>
                  <TableHead>Dataset</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Rows</TableHead>
                  <TableHead>Files</TableHead>
                  <TableHead>Manifest</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => {
                  const isExpanded = expandedRows.has(run.run_id);
                  return (
                    <>
                      <TableRow key={run.run_id}>
                        <TableCell>
                          {run.started_at
                            ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true })
                            : run.created_at
                              ? formatDistanceToNow(new Date(run.created_at), { addSuffix: true })
                              : "-"}
                        </TableCell>
                        <TableCell>{run.dataset}</TableCell>
                        <TableCell>{run.run_type}</TableCell>
                        <TableCell>
                          <Badge variant={STATUS_COLORS[run.status] || "outline"}>
                            {run.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{run.rows_exported.toLocaleString()}</TableCell>
                        <TableCell>{run.files_written}</TableCell>
                        <TableCell>
                          {run.manifest_path ? (
                            <div className="flex items-center gap-2">
                              <code className="text-xs">{run.manifest_path}</code>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => copyToClipboard(run.manifest_path!)}
                                className="h-6 w-6 p-0"
                              >
                                <Copy className="h-3 w-3" />
                              </Button>
                            </div>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                        <TableCell>
                          {run.last_error && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleRow(run.run_id)}
                              className="h-6 w-6 p-0"
                            >
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                      {isExpanded && run.last_error && (
                        <TableRow>
                          <TableCell colSpan={8} className="bg-muted/50">
                            <div className="space-y-1">
                              <div className="text-xs font-medium text-destructive">Error:</div>
                              <code className="text-xs block whitespace-pre-wrap">{run.last_error}</code>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
