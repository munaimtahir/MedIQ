"use client";

import { useState } from "react";
import useSWR from "swr";
import { mutate } from "swr";
import fetcher from "@/lib/fetcher";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import {
  adminNotificationsApi,
  type BroadcastRequest,
  type BroadcastSummaryItem,
  type BroadcastDetailItem,
  type NotificationData,
} from "@/lib/api/adminNotifications";
import { useToast } from "@/components/ui/use-toast";
import { formatDistanceToNow } from "date-fns";
import { Send, Eye, Info, AlertTriangle, AlertCircle } from "lucide-react";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";

const NOTIFICATION_TYPES = [
  { value: "ANNOUNCEMENT", label: "Announcement" },
  { value: "SYSTEM", label: "System" },
  { value: "SECURITY", label: "Security" },
  { value: "COURSE", label: "Course" },
  { value: "REMINDER", label: "Reminder" },
] as const;

const SEVERITY_OPTIONS = [
  { value: "info", label: "Info", icon: Info },
  { value: "warning", label: "Warning", icon: AlertTriangle },
  { value: "critical", label: "Critical", icon: AlertCircle },
] as const;

const TARGET_MODES = [
  { value: "user_ids", label: "Specific Users" },
  { value: "year", label: "By Year" },
  { value: "block", label: "By Block" },
  { value: "cohort", label: "Cohort Filter" },
] as const;

interface AcademicYear {
  id: number;
  display_name: string;
  blocks?: AcademicBlock[];
}

interface AcademicBlock {
  id: number;
  display_name: string;
  code: string;
}

export default function AdminNotificationsPage() {
  const { toast } = useToast();
  const [targetMode, setTargetMode] = useState<"user_ids" | "year" | "block" | "cohort">("user_ids");
  const [userIds, setUserIds] = useState<string>("");
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedBlocks, setSelectedBlocks] = useState<number[]>([]);
  const [cohortId, setCohortId] = useState<string>("");
  const [notificationType, setNotificationType] = useState<string>("ANNOUNCEMENT");
  const [severity, setSeverity] = useState<string>("info");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [actionUrl, setActionUrl] = useState("");
  const [reason, setReason] = useState("");
  const [broadcastDialogOpen, setBroadcastDialogOpen] = useState(false);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [page, setPage] = useState(1);
  const [selectedBroadcast, setSelectedBroadcast] = useState<BroadcastSummaryItem | null>(null);
  const [broadcastDetail, setBroadcastDetail] = useState<BroadcastDetailItem | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const pageSize = 25;

  // Fetch academic structure for year/block selection
  const { data: academicStructure } = useSWR<{ years: AcademicYear[] }>(
    "/api/v1/admin/academic/structure",
    fetcher,
    {
      revalidateOnFocus: false,
    },
  );

  // Fetch recent broadcasts
  const recentKey = `/api/v1/admin/notifications/recent?${new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  }).toString()}`;

  const {
    data: recentData,
    isLoading: recentLoading,
    error: recentError,
  } = useSWR<{
    items: BroadcastSummaryItem[];
    page: number;
    page_size: number;
    total: number;
  }>(recentKey, fetcher, {
    revalidateOnFocus: true,
  });

  const handleBroadcast = async () => {
    setIsBroadcasting(true);
    try {
      // Build target based on mode
      const target: BroadcastRequest["target"] = {
        mode: targetMode,
      };

      if (targetMode === "user_ids") {
        const ids = userIds
          .split(/[,\s]+/)
          .map((id) => id.trim())
          .filter((id) => id.length > 0);
        if (ids.length === 0) {
          toast({
            title: "Error",
            description: "Please provide at least one user ID",
            variant: "destructive",
          });
          setIsBroadcasting(false);
          return;
        }
        target.user_ids = ids;
      } else if (targetMode === "year") {
        if (!selectedYear) {
          toast({
            title: "Error",
            description: "Please select a year",
            variant: "destructive",
          });
          setIsBroadcasting(false);
          return;
        }
        target.year = selectedYear;
      } else if (targetMode === "block") {
        if (!selectedYear || selectedBlocks.length === 0) {
          toast({
            title: "Error",
            description: "Please select a year and at least one block",
            variant: "destructive",
          });
          setIsBroadcasting(false);
          return;
        }
        target.block_ids = selectedBlocks;
      } else if (targetMode === "cohort") {
        target.cohort_id = cohortId || null;
      }

      const result = await adminNotificationsApi.broadcastNotification({
        target,
        notification: {
          type: notificationType as NotificationData["type"],
          title,
          body,
          action_url: actionUrl || null,
          severity: severity as NotificationData["severity"],
        },
        reason,
        confirmation_phrase: "BROADCAST NOTIFICATION",
      });

      // Invalidate recent broadcasts
      await mutate((key) => typeof key === "string" && key.startsWith("/api/v1/admin/notifications/recent"));

      setBroadcastDialogOpen(false);
      setReason("");
      setTitle("");
      setBody("");
      setActionUrl("");
      setUserIds("");
      setSelectedYear(null);
      setSelectedBlocks([]);
      setCohortId("");

      toast({
        title: "Broadcast Complete",
        description: `Notification sent to ${result.created} user(s)`,
      });
    } catch (err: unknown) {
      const error = err as { error?: { message?: string } };
      toast({
        title: "Error",
        description: error.error?.message || "Failed to broadcast notification",
        variant: "destructive",
      });
    } finally {
      setIsBroadcasting(false);
    }
  };

  const canSubmit =
    title.trim().length > 0 &&
    body.trim().length > 0 &&
    ((targetMode === "user_ids" && userIds.trim().length > 0) ||
      (targetMode === "year" && selectedYear !== null) ||
      (targetMode === "block" && selectedYear !== null && selectedBlocks.length > 0) ||
      (targetMode === "cohort"));

  const handleOpenDetail = async (broadcast: BroadcastSummaryItem) => {
    setSelectedBroadcast(broadcast);
    setDetailOpen(true);
    setLoadingDetail(true);
    try {
      const detail = await adminNotificationsApi.getBroadcastDetail(broadcast.id);
      setBroadcastDetail(detail);
    } catch (err) {
      console.error("Failed to load broadcast detail:", err);
      toast({
        title: "Error",
        description: "Failed to load broadcast details",
        variant: "destructive",
      });
    } finally {
      setLoadingDetail(false);
    }
  };

  const getSeverityIcon = (sev: string) => {
    const config = SEVERITY_OPTIONS.find((s) => s.value === sev);
    if (!config) return Info;
    return config.icon;
  };

  const getSeverityBadge = (sev: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive"> = {
      info: "secondary",
      warning: "default",
      critical: "destructive",
    };
    return variants[sev] || "secondary";
  };

  // Get blocks for selected year
  const availableBlocks =
    academicStructure?.years.find((y) => y.id === selectedYear)?.blocks || [];

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Notifications Broadcast</h1>
        <p className="text-muted-foreground">Create and send in-app notifications to users</p>
      </div>

      {/* Broadcast Composer */}
      <Card>
        <CardHeader>
          <CardTitle>Create Broadcast</CardTitle>
          <CardDescription>Compose and send notifications to targeted users</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Target Selector */}
          <div className="space-y-4">
            <Label>Target Audience</Label>
            <RadioGroup value={targetMode} onValueChange={(v) => setTargetMode(v as typeof targetMode)}>
              {TARGET_MODES.map((mode) => (
                <div key={mode.value} className="flex items-center space-x-2">
                  <RadioGroupItem value={mode.value} id={mode.value} />
                  <Label htmlFor={mode.value}>{mode.label}</Label>
                </div>
              ))}
            </RadioGroup>

            {/* Target-specific inputs */}
            {targetMode === "user_ids" && (
              <div>
                <Label htmlFor="user-ids">User IDs (comma or newline separated)</Label>
                <Textarea
                  id="user-ids"
                  value={userIds}
                  onChange={(e) => setUserIds(e.target.value)}
                  placeholder="Enter UUIDs, one per line or comma-separated"
                  rows={4}
                  className="font-mono text-xs"
                />
              </div>
            )}

            {targetMode === "year" && (
              <div>
                <Label htmlFor="year-select">Academic Year</Label>
                <Select
                  value={selectedYear?.toString() || ""}
                  onValueChange={(v) => setSelectedYear(v ? Number(v) : null)}
                >
                  <SelectTrigger id="year-select">
                    <SelectValue placeholder="Select year" />
                  </SelectTrigger>
                  <SelectContent>
                    {academicStructure?.years.map((year) => (
                      <SelectItem key={year.id} value={String(year.id)}>
                        {year.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {targetMode === "block" && (
              <div className="space-y-4">
                <div>
                  <Label htmlFor="block-year-select">Academic Year (required for blocks)</Label>
                  <Select
                    value={selectedYear?.toString() || ""}
                    onValueChange={(v) => {
                      setSelectedYear(v ? Number(v) : null);
                      setSelectedBlocks([]); // Reset blocks when year changes
                    }}
                  >
                    <SelectTrigger id="block-year-select">
                      <SelectValue placeholder="Select year first" />
                    </SelectTrigger>
                    <SelectContent>
                      {academicStructure?.years.map((year) => (
                        <SelectItem key={year.id} value={String(year.id)}>
                          {year.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {selectedYear && (
                  <div>
                    <Label>Select Blocks</Label>
                    <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-2">
                      {availableBlocks.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No blocks available for this year.</p>
                      ) : (
                        availableBlocks.map((block) => (
                          <div key={block.id} className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              id={`block-${block.id}`}
                              checked={selectedBlocks.includes(block.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedBlocks([...selectedBlocks, block.id]);
                                } else {
                                  setSelectedBlocks(selectedBlocks.filter((id) => id !== block.id));
                                }
                              }}
                            />
                            <Label htmlFor={`block-${block.id}`} className="font-normal cursor-pointer">
                              {block.display_name} ({block.code})
                            </Label>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {targetMode === "cohort" && (
              <div>
                <Label htmlFor="cohort-id">Cohort ID</Label>
                <Input
                  id="cohort-id"
                  value={cohortId}
                  onChange={(e) => setCohortId(e.target.value)}
                  placeholder="Enter cohort identifier (future feature)"
                  disabled
                />
                <p className="text-xs text-muted-foreground mt-1">Cohort filtering is not yet implemented</p>
              </div>
            )}
          </div>

          {/* Notification Content */}
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="notification-type">Type</Label>
                <Select value={notificationType} onValueChange={setNotificationType}>
                  <SelectTrigger id="notification-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {NOTIFICATION_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="severity">Severity</Label>
                <Select value={severity} onValueChange={setSeverity}>
                  <SelectTrigger id="severity">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SEVERITY_OPTIONS.map((sev) => {
                      const Icon = sev.icon;
                      return (
                        <SelectItem key={sev.value} value={sev.value}>
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4" />
                            {sev.label}
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Notification title (max 120 chars)"
                maxLength={120}
              />
            </div>

            <div>
              <Label htmlFor="body">Body</Label>
              <Textarea
                id="body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Notification body (markdown/plain text)"
                rows={6}
              />
            </div>

            <div>
              <Label htmlFor="action-url">Action URL (optional)</Label>
              <Input
                id="action-url"
                value={actionUrl}
                onChange={(e) => setActionUrl(e.target.value)}
                placeholder="/student/revision"
              />
              <p className="text-xs text-muted-foreground mt-1">Path only (e.g., /student/revision)</p>
            </div>
          </div>

          {/* Guardrails */}
          <div className="space-y-4 border-t pt-4">
            <div>
              <Label htmlFor="reason">
                Reason <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain why you are broadcasting this notification (minimum 10 characters)..."
                rows={3}
                className={reason.length > 0 && reason.length < 10 ? "border-destructive" : ""}
              />
              {reason.length > 0 && reason.length < 10 && (
                <p className="text-sm text-destructive mt-1">Reason must be at least 10 characters</p>
              )}
              <p className="text-xs text-muted-foreground mt-1">
                You will be asked to confirm with a typed phrase before sending.
              </p>
            </div>
          </div>

          <Button
            onClick={() => setBroadcastDialogOpen(true)}
            disabled={!canSubmit}
            className="w-full"
            size="lg"
          >
            <Send className="h-4 w-4 mr-2" />
            Broadcast Notification
          </Button>
        </CardContent>
      </Card>

      {/* Recent Broadcasts */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Broadcasts</CardTitle>
          <CardDescription>History of notification broadcasts</CardDescription>
        </CardHeader>
        <CardContent>
          {recentLoading ? (
            <SkeletonTable rows={5} cols={6} />
          ) : recentError ? (
            <EmptyState title="Failed to load recent broadcasts" />
          ) : !recentData || recentData.items.length === 0 ? (
            <EmptyState title="No broadcasts yet" />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Created At</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Target</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentData.items.map((item) => {
                    const SeverityIcon = getSeverityIcon(item.severity);
                    return (
                      <TableRow key={item.id}>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                        </TableCell>
                        <TableCell className="max-w-xs truncate">{item.title}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{item.type}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <SeverityIcon className="h-4 w-4" />
                            <Badge variant={getSeverityBadge(item.severity)}>{item.severity}</Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs">
                          {item.target_summary.mode === "year" && item.target_summary.year
                            ? `Year ${item.target_summary.year}`
                            : item.target_summary.mode === "block" && item.target_summary.block_ids
                              ? `${item.target_summary.block_ids.length} block(s)`
                              : item.target_summary.mode === "user_ids"
                                ? `${item.target_summary.user_count} user(s)`
                                : item.target_summary.mode}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenDetail(item)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Pagination */}
              {Math.ceil((recentData.total || 0) / pageSize) > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <Button
                    variant="outline"
                    disabled={page === 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {Math.ceil((recentData.total || 0) / pageSize)} (Total: {recentData.total})
                  </span>
                  <Button
                    variant="outline"
                    disabled={page >= Math.ceil((recentData.total || 0) / pageSize)}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Broadcast Confirmation Modal */}
      <PoliceConfirmModal
        open={broadcastDialogOpen}
        onOpenChange={setBroadcastDialogOpen}
        actionTitle="Broadcast Notification"
        requiredPhrase="BROADCAST NOTIFICATION"
        reason={reason}
        onReasonChange={setReason}
        onConfirm={handleBroadcast}
        isSubmitting={isBroadcasting}
        variant="default"
        jsonDiff={{
          previous: {},
          current: {
            target:
              targetMode === "user_ids"
                ? `${userIds.split(/[,\s]+/).filter((id) => id.trim().length > 0).length} user(s)`
                : targetMode === "year"
                  ? `Year ${selectedYear}`
                  : targetMode === "block"
                    ? `${selectedBlocks.length} block(s)`
                    : "Cohort filter",
            notification: {
              type: notificationType,
              severity,
              title,
              body: body.substring(0, 200) + (body.length > 200 ? "..." : ""),
              action_url: actionUrl || null,
            },
          },
        }}
      />

      {/* Broadcast Detail Drawer */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Broadcast Details</DialogTitle>
            <DialogDescription>Full notification content and audit metadata</DialogDescription>
          </DialogHeader>
          {loadingDetail ? (
            <div className="py-8">
              <SkeletonTable rows={3} cols={2} />
            </div>
          ) : broadcastDetail ? (
            <div className="space-y-6 py-4">
              {/* Notification Content */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Notification Content</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label className="text-sm text-muted-foreground">Title</Label>
                    <p className="text-sm font-semibold mt-1">{broadcastDetail.title}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Type</Label>
                    <div className="mt-1">
                      <Badge variant="outline">{broadcastDetail.type}</Badge>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Severity</Label>
                    <div className="flex items-center gap-2 mt-1">
                      {(() => {
                        const Icon = getSeverityIcon(broadcastDetail.severity);
                        return (
                          <>
                            <Icon className="h-4 w-4" />
                            <Badge variant={getSeverityBadge(broadcastDetail.severity)}>
                              {broadcastDetail.severity}
                            </Badge>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Action URL</Label>
                    <p className="text-sm mt-1 font-mono text-xs">
                      {broadcastDetail.action_url || "None"}
                    </p>
                  </div>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Body</Label>
                  <div className="mt-1 rounded-md bg-muted p-3 text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {broadcastDetail.body || "No body content"}
                  </div>
                </div>
              </div>

              {/* Target Resolution */}
              <div className="space-y-2 border-t pt-4">
                <h3 className="text-lg font-semibold">Target Resolution</h3>
                <div className="rounded-md bg-muted p-3">
                  <div className="grid gap-2 text-sm">
                    <div>
                      <span className="font-semibold">Mode:</span> {broadcastDetail.target_summary.mode}
                    </div>
                    <div>
                      <span className="font-semibold">Users Notified:</span> {broadcastDetail.target_summary.user_count}
                    </div>
                    {broadcastDetail.target_summary.year && (
                      <div>
                        <span className="font-semibold">Year:</span> {broadcastDetail.target_summary.year}
                      </div>
                    )}
                    {broadcastDetail.target_summary.block_ids && broadcastDetail.target_summary.block_ids.length > 0 && (
                      <div>
                        <span className="font-semibold">Blocks:</span> {broadcastDetail.target_summary.block_ids.join(", ")}
                      </div>
                    )}
                    {broadcastDetail.target_summary.cohort_id && (
                      <div>
                        <span className="font-semibold">Cohort ID:</span> {broadcastDetail.target_summary.cohort_id}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Audit Metadata */}
              <div className="space-y-2 border-t pt-4">
                <h3 className="text-lg font-semibold">Audit Metadata</h3>
                {broadcastDetail.audit_metadata.reason && (
                  <div className="mb-4">
                    <Label className="text-sm text-muted-foreground">Reason</Label>
                    <p className="text-sm mt-1 rounded-md bg-muted p-3">{broadcastDetail.audit_metadata.reason}</p>
                  </div>
                )}
                <div className="space-y-3">
                  {broadcastDetail.audit_metadata.after && (
                    <div>
                      <Label className="text-sm text-muted-foreground">After (Notification Data)</Label>
                      <pre className="mt-1 overflow-x-auto rounded-md bg-muted p-3 text-xs max-h-48">
                        {JSON.stringify(broadcastDetail.audit_metadata.after, null, 2)}
                      </pre>
                    </div>
                  )}
                  {broadcastDetail.audit_metadata.meta && (
                    <div>
                      <Label className="text-sm text-muted-foreground">Meta (Target & Context)</Label>
                      <pre className="mt-1 overflow-x-auto rounded-md bg-muted p-3 text-xs max-h-48">
                        {JSON.stringify(broadcastDetail.audit_metadata.meta, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              {/* Timestamp */}
              <div className="border-t pt-4 text-xs text-muted-foreground">
                Created: {new Date(broadcastDetail.created_at).toLocaleString()}
                {broadcastDetail.created_by && ` • By: ${broadcastDetail.created_by}`}
              </div>
            </div>
          ) : selectedBroadcast ? (
            <div className="py-8 text-center text-muted-foreground">
              Failed to load broadcast details
            </div>
          ) : null}
          <DialogFooter>
            <Button onClick={() => {
              setDetailOpen(false);
              setBroadcastDetail(null);
            }}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
