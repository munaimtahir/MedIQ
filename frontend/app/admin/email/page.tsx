"use client";

import { useState } from "react";
import useSWR from "swr";
import { mutate } from "swr";
import fetcher from "@/lib/fetcher";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import { adminEmailApi, type EmailRuntimeResponse, type EmailOutboxItem } from "@/lib/api/adminEmail";
import { useToast } from "@/components/ui/use-toast";
import { formatDistanceToNow } from "date-fns";
import {
  Mail,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Eye,
  Copy,
  Check,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const EMAIL_MODES = [
  { value: "disabled", label: "Disabled", phrase: "SWITCH EMAIL TO DISABLED" },
  { value: "shadow", label: "Shadow", phrase: "SWITCH EMAIL TO SHADOW" },
  { value: "active", label: "Active", phrase: "SWITCH EMAIL TO ACTIVE" },
] as const;

const EMAIL_STATUSES = [
  { value: "", label: "All Statuses" },
  { value: "queued", label: "Queued" },
  { value: "sending", label: "Sending" },
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
  { value: "blocked_disabled", label: "Blocked (Disabled)" },
  { value: "blocked_frozen", label: "Blocked (Frozen)" },
  { value: "shadow_logged", label: "Shadow Logged" },
] as const;

interface EmailOutboxDetail extends EmailOutboxItem {
  body_text?: string | null;
  body_html?: string | null;
  template_vars?: Record<string, unknown>;
}

function ModePill({ mode, label }: { mode: string; label: string }) {
  const variant = mode === "active" ? "default" : mode === "shadow" ? "secondary" : "outline";
  return <Badge variant={variant}>{label}</Badge>;
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    sent: "default",
    queued: "secondary",
    sending: "secondary",
    failed: "destructive",
    blocked_disabled: "destructive",
    blocked_frozen: "destructive",
    shadow_logged: "outline",
  };
  const icons: Record<string, typeof CheckCircle2> = {
    sent: CheckCircle2,
    failed: XCircle,
    sending: Clock,
    blocked_disabled: XCircle,
    blocked_frozen: XCircle,
  };
  const Icon = icons[status] || Mail;
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-4 w-4" />
      <Badge variant={variants[status] || "secondary"}>{status}</Badge>
    </div>
  );
}

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2">
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {label && <span className="ml-1 text-xs">{label}</span>}
    </Button>
  );
}

export default function AdminEmailPage() {
  const { toast } = useToast();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<EmailOutboxDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [switchDialogOpen, setSwitchDialogOpen] = useState(false);
  const [drainDialogOpen, setDrainDialogOpen] = useState(false);
  const [switchMode, setSwitchMode] = useState<string>("");
  const [switchReason, setSwitchReason] = useState("");
  const [drainLimit, setDrainLimit] = useState(50);
  const [drainReason, setDrainReason] = useState("");
  const [drainPhrase, setDrainPhrase] = useState("");
  const [isSwitching, setIsSwitching] = useState(false);
  const [isDraining, setIsDraining] = useState(false);

  const pageSize = 25;

  // SWR hooks
  const {
    data: runtime,
    isLoading: runtimeLoading,
    mutate: refetchRuntime,
  } = useSWR("/api/v1/admin/email/runtime", fetcher, {
    refreshInterval: 30000, // Refetch every 30s
  });

  const outboxKey = `/api/v1/admin/email/outbox?${new URLSearchParams({
    ...(statusFilter && { status: statusFilter }),
    page: String(page),
    page_size: String(pageSize),
  }).toString()}`;

  const {
    data: outboxData,
    isLoading: outboxLoading,
    error: outboxError,
    mutate: refetchOutbox,
  } = useSWR(outboxKey, fetcher, {
    revalidateOnFocus: true,
  });

  const handleSwitchMode = async () => {
    const modeConfig = EMAIL_MODES.find((m) => m.value === switchMode);
    if (!modeConfig) return;

    setIsSwitching(true);
    try {
      await adminEmailApi.switchMode(switchMode, switchReason, modeConfig.phrase);
      await mutate("/api/v1/admin/email/runtime");
      await mutate((key) => typeof key === "string" && key.startsWith("/api/v1/admin/email/outbox"));
      setSwitchDialogOpen(false);
      setSwitchMode("");
      setSwitchReason("");
      toast({
        title: "Success",
        description: "Email mode switched successfully",
      });
    } catch (err: unknown) {
      const error = err as { error?: { message?: string } };
      toast({
        title: "Error",
        description: error.error?.message || "Failed to switch email mode",
        variant: "destructive",
      });
    } finally {
      setIsSwitching(false);
    }
  };

  const handleDrain = async () => {
    if (drainPhrase !== "DRAIN EMAIL OUTBOX" || drainReason.trim().length < 10) {
      return;
    }

    setIsDraining(true);
    try {
      const result = await adminEmailApi.drainOutbox({
        limit: drainLimit,
        reason: drainReason,
        phrase: "DRAIN EMAIL OUTBOX",
      });
      await mutate((key) => typeof key === "string" && key.startsWith("/api/v1/admin/email/outbox"));
      await mutate("/api/v1/admin/email/runtime");
      setDrainDialogOpen(false);
      setDrainReason("");
      setDrainPhrase("");
      toast({
        title: "Drain Complete",
        description: `Processed ${result.attempted} emails: ${result.sent} sent, ${result.failed} failed, ${result.skipped} skipped`,
      });
    } catch (err: unknown) {
      const error = err as { error?: { message?: string } };
      toast({
        title: "Error",
        description: error.error?.message || "Failed to drain outbox",
        variant: "destructive",
      });
    } finally {
      setIsDraining(false);
    }
  };

  const handleViewDetail = async (id: string) => {
    try {
      const item = await adminEmailApi.getOutboxItem(id);
      setSelectedItem(item);
      setDetailOpen(true);
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to load email details",
        variant: "destructive",
      });
    }
  };

  const handleSwitchMode = () => {
    const modeConfig = EMAIL_MODES.find((m) => m.value === switchMode);
    if (!modeConfig) return;
    switchModeMutation({
      mode: switchMode,
      reason: switchReason,
      phrase: modeConfig.phrase,
    });
  };

  const handleDrain = () => {
    drainMutation({
      limit: drainLimit,
      reason: drainReason,
      phrase: "DRAIN EMAIL OUTBOX",
    });
  };

  const canSwitchToActive =
    runtime?.provider.configured && !runtime?.freeze && runtime?.effective_mode !== "active";
  const blockingReasonsForActive: string[] = [];
  if (!runtime?.provider.configured) blockingReasonsForActive.push("Provider not configured");
  if (runtime?.freeze) blockingReasonsForActive.push("Email system is frozen");
  if (runtime?.blocking_reasons) blockingReasonsForActive.push(...runtime.blocking_reasons);

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Email Ops</h1>
        <p className="text-muted-foreground">Email runtime configuration and outbox management</p>
      </div>

      {/* Runtime Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Email Status</CardTitle>
          <CardDescription>Current email system state</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {runtimeLoading ? (
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded w-1/4 animate-pulse" />
              <div className="h-4 bg-muted rounded w-1/3 animate-pulse" />
            </div>
          ) : runtime ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-sm text-muted-foreground">Requested Mode</Label>
                  <div className="mt-1">
                    <ModePill mode={runtime.requested_mode} label={runtime.requested_mode} />
                  </div>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Effective Mode</Label>
                  <div className="mt-1">
                    <ModePill mode={runtime.effective_mode} label={runtime.effective_mode} />
                  </div>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Provider</Label>
                  <div className="mt-1">
                    <Badge variant={runtime.provider.configured ? "default" : "secondary"}>
                      {runtime.provider.type} {runtime.provider.configured ? "✓" : "✗"}
                    </Badge>
                  </div>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Freeze</Label>
                  <div className="mt-1">
                    <Badge variant={runtime.freeze ? "destructive" : "default"}>
                      {runtime.freeze ? "Frozen" : "Active"}
                    </Badge>
                  </div>
                </div>
              </div>

              {runtime.warnings && runtime.warnings.length > 0 && (
                <div className="rounded-md bg-yellow-50 p-3 border border-yellow-200">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <div className="font-medium text-yellow-800">Warnings</div>
                      <ul className="mt-1 text-sm text-yellow-700 list-disc list-inside">
                        {runtime.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {runtime.blocking_reasons && runtime.blocking_reasons.length > 0 && (
                <div className="rounded-md bg-red-50 p-3 border border-red-200">
                  <div className="flex items-start gap-2">
                    <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                    <div>
                      <div className="font-medium text-red-800">Blocking Reasons</div>
                      <ul className="mt-1 text-sm text-red-700 list-disc list-inside">
                        {runtime.blocking_reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                {EMAIL_MODES.map((mode) => {
                  const isDisabled =
                    mode.value === "active" && (!canSwitchToActive || runtime.effective_mode === "active");
                  const button = (
                    <Button
                      key={mode.value}
                      variant={runtime.requested_mode === mode.value ? "default" : "outline"}
                      disabled={isDisabled || isSwitching}
                      onClick={() => {
                        setSwitchMode(mode.value);
                        setSwitchDialogOpen(true);
                      }}
                    >
                      Switch to {mode.label}
                    </Button>
                  );

                  if (isDisabled && blockingReasonsForActive.length > 0) {
                    return (
                      <TooltipProvider key={mode.value}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span>{button}</span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{blockingReasonsForActive.join(", ")}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    );
                  }

                  return button;
                })}
              </div>
            </>
          ) : (
            <EmptyState title="Failed to load runtime config" />
          )}
        </CardContent>
      </Card>

      {/* Outbox */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Email Outbox</CardTitle>
              <CardDescription>Queued and sent emails</CardDescription>
            </div>
            <Button onClick={() => refetchOutbox()} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <Select
              value={statusFilter}
              onValueChange={(v) => {
                setStatusFilter(v);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                {EMAIL_STATUSES.map((status) => (
                  <SelectItem key={status.value} value={status.value}>
                    {status.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={() => setDrainDialogOpen(true)} variant="outline">
              Drain Outbox
            </Button>
          </div>

          {outboxLoading ? (
            <SkeletonTable rows={5} cols={7} />
          ) : outboxError ? (
            <ErrorState
              title="Failed to load outbox"
              description={outboxError instanceof Error ? outboxError.message : "Unknown error"}
              onAction={() => refetchOutbox()}
            />
          ) : !outboxData || outboxData.items.length === 0 ? (
            <EmptyState title="No emails in outbox" />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Created At</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead>Template</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Attempts</TableHead>
                    <TableHead>Sent At</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {outboxData.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{item.to_email}</TableCell>
                      <TableCell className="max-w-xs truncate">{item.subject}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{item.template_key}</Badge>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={item.status} />
                      </TableCell>
                      <TableCell>{item.attempts}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {item.sent_at
                          ? formatDistanceToNow(new Date(item.sent_at), { addSuffix: true })
                          : "-"}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={() => handleViewDetail(item.id)}>
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {Math.ceil((outboxData.total || 0) / pageSize) > 1 && (
                <div className="flex items-center justify-between">
                  <Button
                    variant="outline"
                    disabled={page === 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {Math.ceil((outboxData.total || 0) / pageSize)} (Total:{" "}
                    {outboxData.total})
                  </span>
                  <Button
                    variant="outline"
                    disabled={page >= Math.ceil((outboxData.total || 0) / pageSize)}
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

      {/* Switch Mode Dialog */}
      <PoliceConfirmModal
        open={switchDialogOpen}
        onOpenChange={setSwitchDialogOpen}
        actionTitle={`Switch Email to ${EMAIL_MODES.find((m) => m.value === switchMode)?.label || ""}`}
        requiredPhrase={EMAIL_MODES.find((m) => m.value === switchMode)?.phrase || ""}
        reason={switchReason}
        onReasonChange={setSwitchReason}
        onConfirm={handleSwitchMode}
        isSubmitting={isSwitching}
        variant="default"
      />

      {/* Drain Dialog - Custom with limit input */}
      <Dialog open={drainDialogOpen} onOpenChange={setDrainDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Drain Email Outbox</DialogTitle>
            <DialogDescription>
              Process queued emails from the outbox. This requires a confirmation phrase.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div>
              <Label htmlFor="drain-limit">Limit</Label>
              <Input
                id="drain-limit"
                type="number"
                min={1}
                max={500}
                value={drainLimit}
                onChange={(e) => setDrainLimit(Number(e.target.value))}
                disabled={isDraining}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">Max 500 emails per drain</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="drain-reason">
                Reason <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="drain-reason"
                placeholder="Explain why you are draining the outbox (minimum 10 characters)..."
                value={drainReason}
                onChange={(e) => setDrainReason(e.target.value)}
                rows={3}
                disabled={isDraining}
                className={drainReason.length > 0 && drainReason.length < 10 ? "border-destructive" : ""}
              />
              {drainReason.length > 0 && drainReason.length < 10 && (
                <p className="text-sm text-destructive">Reason must be at least 10 characters</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="drain-phrase">
                Type confirmation phrase <span className="text-destructive">*</span>
              </Label>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Required phrase:</span>
                  <code className="px-2 py-1 bg-muted rounded font-mono">DRAIN EMAIL OUTBOX</code>
                </div>
                <Input
                  id="drain-phrase"
                  value={drainPhrase}
                  onChange={(e) => setDrainPhrase(e.target.value)}
                  placeholder="Type the phrase above..."
                  disabled={isDraining}
                  className={drainPhrase && drainPhrase !== "DRAIN EMAIL OUTBOX" ? "border-destructive" : ""}
                />
                <div className="flex items-center gap-2">
                  {drainPhrase === "DRAIN EMAIL OUTBOX" ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <Badge variant="default" className="text-xs bg-green-600">
                        Confirmed
                      </Badge>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 text-destructive" />
                      <Badge variant="destructive" className="text-xs">
                        Not confirmed
                      </Badge>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDrainDialogOpen(false)} disabled={isDraining}>
              Cancel
            </Button>
            <Button
              onClick={handleDrain}
              disabled={
                !(
                  drainPhrase === "DRAIN EMAIL OUTBOX" &&
                  drainReason.trim().length >= 10 &&
                  !isDraining
                )
              }
            >
              {isDraining ? "Draining..." : "Drain Outbox"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Email Detail Drawer */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Email Details</DialogTitle>
            <DialogDescription>View email outbox item details</DialogDescription>
          </DialogHeader>
          {selectedItem && (
            <div className="space-y-4 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-sm text-muted-foreground">ID</Label>
                  <div className="flex items-center gap-2 mt-1">
                    <p className="font-mono text-xs">{selectedItem.id}</p>
                    <CopyButton text={selectedItem.id} />
                  </div>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">To Email</Label>
                  <p className="font-mono text-sm">{selectedItem.to_email}</p>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">To Name</Label>
                  <p className="text-sm">{selectedItem.to_name || "-"}</p>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Subject</Label>
                  <p className="text-sm">{selectedItem.subject}</p>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Template</Label>
                  <Badge variant="outline">{selectedItem.template_key}</Badge>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Status</Label>
                  <StatusBadge status={selectedItem.status} />
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Provider</Label>
                  <p className="text-sm">{selectedItem.provider || "-"}</p>
                </div>
                {selectedItem.provider_message_id && (
                  <div>
                    <Label className="text-sm text-muted-foreground">Provider Message ID</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="font-mono text-xs">{selectedItem.provider_message_id}</p>
                      <CopyButton text={selectedItem.provider_message_id} />
                    </div>
                  </div>
                )}
                <div>
                  <Label className="text-sm text-muted-foreground">Attempts</Label>
                  <p className="text-sm">{selectedItem.attempts}</p>
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Created</Label>
                  <p className="text-sm">{new Date(selectedItem.created_at).toLocaleString()}</p>
                </div>
                {selectedItem.sent_at && (
                  <div>
                    <Label className="text-sm text-muted-foreground">Sent At</Label>
                    <p className="text-sm">{new Date(selectedItem.sent_at).toLocaleString()}</p>
                  </div>
                )}
                {selectedItem.last_error && (
                  <div className="md:col-span-2">
                    <Label className="text-sm text-muted-foreground">Last Error</Label>
                    <p className="text-sm text-red-600 font-mono bg-red-50 p-2 rounded mt-1">
                      {selectedItem.last_error}
                    </p>
                  </div>
                )}
              </div>

              {selectedItem.template_vars && Object.keys(selectedItem.template_vars).length > 0 && (
                <div>
                  <Label className="text-sm text-muted-foreground">Template Variables</Label>
                  <pre className="mt-1 overflow-x-auto rounded-md bg-muted p-3 text-xs max-h-48">
                    {JSON.stringify(selectedItem.template_vars, null, 2)}
                  </pre>
                </div>
              )}

              {(selectedItem.body_text || selectedItem.body_html) && (
                <div>
                  <Label className="text-sm text-muted-foreground">Body Preview</Label>
                  <Tabs defaultValue="text" className="mt-2">
                    <TabsList>
                      {selectedItem.body_text && <TabsTrigger value="text">Text</TabsTrigger>}
                      {selectedItem.body_html && <TabsTrigger value="html">HTML</TabsTrigger>}
                    </TabsList>
                    {selectedItem.body_text && (
                      <TabsContent value="text">
                        <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs max-h-64 whitespace-pre-wrap">
                          {selectedItem.body_text}
                        </pre>
                      </TabsContent>
                    )}
                    {selectedItem.body_html && (
                      <TabsContent value="html">
                        <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs max-h-64 whitespace-pre-wrap">
                          {selectedItem.body_html.replace(/</g, "&lt;").replace(/>/g, "&gt;")}
                        </pre>
                      </TabsContent>
                    )}
                  </Tabs>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setDetailOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
