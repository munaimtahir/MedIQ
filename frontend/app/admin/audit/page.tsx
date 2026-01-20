"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { adminAuditApi } from "@/lib/admin/auditApi";
import type { AuditLogItem, AuditLogQuery } from "@/lib/types/question-cms";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { FileSearch, Eye, X } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const ACTION_TYPES = [
  "question.create",
  "question.update",
  "question.submit",
  "question.approve",
  "question.reject",
  "question.publish",
  "question.unpublish",
];

export default function AuditPage() {
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const [filters, setFilters] = useState<AuditLogQuery>({
    page: 1,
    page_size: 50,
  });

  const loadAuditLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminAuditApi.queryAuditLog(filters);
      setAuditLogs(data);
    } catch (err) {
      console.error("Failed to load audit log:", err);
      setError(err instanceof Error ? err : new Error("Failed to load audit log"));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadAuditLogs();
  }, [loadAuditLogs]);

  const handleFilterChange = (key: keyof AuditLogQuery, value: string | undefined) => {
    setFilters({ ...filters, [key]: value, page: 1 });
  };

  const handleResetFilters = () => {
    setFilters({ page: 1, page_size: 50 });
  };

  const handleViewDetails = (log: AuditLogItem) => {
    setSelectedLog(log);
    setDetailModalOpen(true);
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return {
        relative: formatDistanceToNow(date, { addSuffix: true }),
        absolute: date.toLocaleString(),
      };
    } catch {
      return { relative: dateStr, absolute: dateStr };
    }
  };

  const getActionBadgeColor = (action: string) => {
    if (action.includes("create")) return "bg-green-500";
    if (action.includes("update") || action.includes("edit")) return "bg-blue-500";
    if (action.includes("approve") || action.includes("publish")) return "bg-purple-500";
    if (action.includes("reject") || action.includes("unpublish")) return "bg-orange-500";
    if (action.includes("delete")) return "bg-red-500";
    return "bg-gray-500";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <FileSearch className="h-8 w-8" />
            <h1 className="text-3xl font-bold">Audit Log</h1>
          </div>
          <p className="text-muted-foreground">Track all system actions and changes</p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Filters</CardTitle>
              <CardDescription>Filter audit log entries</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={handleResetFilters}>
              <X className="mr-2 h-4 w-4" />
              Reset
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="entity_type">Entity Type</Label>
              <Select
                value={filters.entity_type || ""}
                onValueChange={(v) => handleFilterChange("entity_type", v || undefined)}
              >
                <SelectTrigger id="entity_type">
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All types</SelectItem>
                  <SelectItem value="QUESTION">Question</SelectItem>
                  <SelectItem value="MEDIA">Media</SelectItem>
                  <SelectItem value="USER">User</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="action">Action</Label>
              <Select
                value={filters.action || ""}
                onValueChange={(v) => handleFilterChange("action", v || undefined)}
              >
                <SelectTrigger id="action">
                  <SelectValue placeholder="All actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All actions</SelectItem>
                  {ACTION_TYPES.map((action) => (
                    <SelectItem key={action} value={action}>
                      {action}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="entity_id">Entity ID</Label>
              <Input
                id="entity_id"
                value={filters.entity_id || ""}
                onChange={(e) => handleFilterChange("entity_id", e.target.value || undefined)}
                placeholder="Filter by entity ID..."
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Trail</CardTitle>
          <CardDescription>
            {!loading && !error && `${auditLogs.length} entries found`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <SkeletonTable rows={10} cols={6} />
          ) : error ? (
            <ErrorState
              variant="card"
              title="Failed to load audit log"
              description={error.message || "An error occurred while loading the audit log."}
              actionLabel="Retry"
              onAction={loadAuditLogs}
            />
          ) : auditLogs.length === 0 ? (
            <EmptyState
              variant="card"
              title="No audit logs found"
              description="No audit logs match your current filters."
              icon={<FileSearch className="h-8 w-8 text-slate-400" />}
              actionLabel="Reset Filters"
              onAction={handleResetFilters}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">Timestamp</TableHead>
                  <TableHead className="w-[150px]">Actor</TableHead>
                  <TableHead className="w-[150px]">Action</TableHead>
                  <TableHead className="w-[100px]">Entity Type</TableHead>
                  <TableHead className="w-[250px]">Entity ID</TableHead>
                  <TableHead className="w-[100px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.map((log) => {
                  const date = formatDate(log.created_at);
                  return (
                    <TableRow key={log.id} className="hover:bg-muted/50">
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="text-sm">{date.relative}</span>
                          <span className="text-xs text-muted-foreground">{date.absolute}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="text-sm truncate">{log.actor_name || "Unknown"}</span>
                          <span className="text-xs text-muted-foreground truncate">
                            {log.actor_user_id.substring(0, 8)}...
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={getActionBadgeColor(log.action)}>{log.action}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{log.entity_type}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-mono">{log.entity_id}</span>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetails(log)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Detail Modal */}
      <Dialog open={detailModalOpen} onOpenChange={setDetailModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Audit Log Details</DialogTitle>
            <DialogDescription>
              Detailed information about this audit log entry
            </DialogDescription>
          </DialogHeader>
          {selectedLog && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground">Timestamp</Label>
                  <p className="text-sm">{new Date(selectedLog.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Action</Label>
                  <p className="text-sm">{selectedLog.action}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Entity Type</Label>
                  <p className="text-sm">{selectedLog.entity_type}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Entity ID</Label>
                  <p className="text-sm font-mono text-xs">{selectedLog.entity_id}</p>
                </div>
              </div>

              {selectedLog.before && (
                <div>
                  <Label className="text-xs text-muted-foreground">Before</Label>
                  <pre className="mt-1 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.before, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.after && (
                <div>
                  <Label className="text-xs text-muted-foreground">After</Label>
                  <pre className="mt-1 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.after, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.meta && (
                <div>
                  <Label className="text-xs text-muted-foreground">Metadata</Label>
                  <pre className="mt-1 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.meta, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
