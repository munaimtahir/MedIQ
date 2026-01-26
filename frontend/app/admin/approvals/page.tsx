"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { usePendingApprovals, useApproveRequest, useRejectRequest, useRequestApproval } from "@/lib/admin/approvals/hooks";
import { AlertTriangle, CheckCircle2, XCircle, Clock, Plus } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";
import { notify } from "@/lib/notify";
import type { ApprovalRequest } from "@/lib/admin/approvals/api";

const ACTION_LABELS: Record<string, string> = {
  PROFILE_SWITCH_PRIMARY: "Switch to PRIMARY Profile",
  PROFILE_SWITCH_FALLBACK: "Switch to FALLBACK Profile",
  IRT_ACTIVATE: "Activate IRT",
  ELASTICSEARCH_ENABLE: "Enable Elasticsearch",
  NEO4J_ENABLE: "Enable Neo4j",
  SNOWFLAKE_EXPORT_ENABLE: "Enable Snowflake Export",
};

const CONFIRMATION_PHRASES: Record<string, string> = {
  PROFILE_SWITCH_PRIMARY: "SWITCH TO V1_PRIMARY",
  PROFILE_SWITCH_FALLBACK: "SWITCH TO V0_FALLBACK",
  IRT_ACTIVATE: "ACTIVATE IRT",
  ELASTICSEARCH_ENABLE: "ENABLE ELASTICSEARCH",
  NEO4J_ENABLE: "ENABLE NEO4J",
  SNOWFLAKE_EXPORT_ENABLE: "ENABLE SNOWFLAKE EXPORT",
};

export default function ApprovalsPage() {
  const { data, isLoading, refetch } = usePendingApprovals();
  const approveMutation = useApproveRequest();
  const rejectMutation = useRejectRequest();
  const requestMutation = useRequestApproval();

  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [requestDialogOpen, setRequestDialogOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<string | null>(null);
  const [confirmationPhrase, setConfirmationPhrase] = useState("");
  const [requestForm, setRequestForm] = useState<Partial<ApprovalRequest>>({
    action_type: "PROFILE_SWITCH_PRIMARY",
    action_payload: {},
    reason: "",
    confirmation_phrase: "",
  });

  const approvals = data?.approvals || [];
  const pending = approvals.filter((a) => a.status === "PENDING");
  const approved = approvals.filter((a) => a.status === "APPROVED");
  const rejected = approvals.filter((a) => a.status === "REJECTED");

  const handleApproveClick = (requestId: string) => {
    setSelectedRequest(requestId);
    setConfirmationPhrase("");
    setApproveDialogOpen(true);
  };

  const handleApprove = () => {
    if (!selectedRequest) return;

    const approval = approvals.find((a) => a.request_id === selectedRequest);
    if (!approval) return;

    approveMutation.mutate(
      {
        requestId: selectedRequest,
        data: { confirmation_phrase: confirmationPhrase },
      },
      {
        onSuccess: () => {
          setApproveDialogOpen(false);
          setSelectedRequest(null);
          setConfirmationPhrase("");
          refetch();
        },
      }
    );
  };

  const handleRejectClick = (requestId: string) => {
    setSelectedRequest(requestId);
    setRejectDialogOpen(true);
  };

  const handleReject = () => {
    if (!selectedRequest) return;
    rejectMutation.mutate(selectedRequest, {
      onSuccess: () => {
        setRejectDialogOpen(false);
        setSelectedRequest(null);
        refetch();
      },
    });
  };

  const handleRequestSubmit = () => {
    if (!requestForm.action_type || !requestForm.reason || !requestForm.confirmation_phrase) {
      notify.error("Validation failed", "Please fill in all required fields");
      return;
    }

    requestMutation.mutate(requestForm as ApprovalRequest, {
      onSuccess: () => {
        setRequestDialogOpen(false);
        setRequestForm({
          action_type: "PROFILE_SWITCH_PRIMARY",
          action_payload: {},
          reason: "",
          confirmation_phrase: "",
        });
        refetch();
      },
    });
  };

  const selectedApproval = selectedRequest
    ? approvals.find((a) => a.request_id === selectedRequest)
    : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Approvals</h1>
          <p className="text-muted-foreground">Two-person approval system for high-risk actions</p>
        </div>
        <Button onClick={() => setRequestDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Request Approval
        </Button>
      </div>

      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending">
            Pending ({pending.length})
          </TabsTrigger>
          <TabsTrigger value="approved">
            Approved ({approved.length})
          </TabsTrigger>
          <TabsTrigger value="rejected">
            Rejected ({rejected.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="space-y-4">
          {isLoading ? (
            <Card>
              <CardContent className="py-8">
                <div className="h-32 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ) : pending.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No pending approvals
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Pending Approvals</CardTitle>
                <CardDescription>
                  High-risk actions requiring two-person approval in production
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Action</TableHead>
                      <TableHead>Requested By</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pending.map((approval) => (
                      <TableRow key={approval.request_id}>
                        <TableCell>
                          <Badge variant="outline">
                            {ACTION_LABELS[approval.action_type] || approval.action_type}
                          </Badge>
                        </TableCell>
                        <TableCell>{approval.requested_by.email || "Unknown"}</TableCell>
                        <TableCell className="max-w-md truncate">
                          {approval.requested_action?.reason || "No reason provided"}
                        </TableCell>
                        <TableCell>
                          {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={() => handleApproveClick(approval.request_id)}
                              disabled={approveMutation.isPending || rejectMutation.isPending}
                            >
                              <CheckCircle2 className="h-4 w-4 mr-1" />
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRejectClick(approval.request_id)}
                              disabled={approveMutation.isPending || rejectMutation.isPending}
                            >
                              <XCircle className="h-4 w-4 mr-1" />
                              Reject
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="approved" className="space-y-4">
          {approved.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No approved requests
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Approved Requests</CardTitle>
                <CardDescription>Recently approved high-risk actions</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Action</TableHead>
                      <TableHead>Requested By</TableHead>
                      <TableHead>Approved By</TableHead>
                      <TableHead>Decided</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {approved.map((approval) => (
                      <TableRow key={approval.request_id}>
                        <TableCell>
                          <Badge variant="default">
                            {ACTION_LABELS[approval.action_type] || approval.action_type}
                          </Badge>
                        </TableCell>
                        <TableCell>{approval.requested_by.email || "Unknown"}</TableCell>
                        <TableCell>
                          {approval.approved_by?.email || "Unknown"}
                        </TableCell>
                        <TableCell>
                          {approval.decided_at
                            ? formatDistanceToNow(new Date(approval.decided_at), { addSuffix: true })
                            : "N/A"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="rejected" className="space-y-4">
          {rejected.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No rejected requests
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Rejected Requests</CardTitle>
                <CardDescription>Recently rejected approval requests</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Action</TableHead>
                      <TableHead>Requested By</TableHead>
                      <TableHead>Rejected By</TableHead>
                      <TableHead>Decided</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rejected.map((approval) => (
                      <TableRow key={approval.request_id}>
                        <TableCell>
                          <Badge variant="destructive">
                            {ACTION_LABELS[approval.action_type] || approval.action_type}
                          </Badge>
                        </TableCell>
                        <TableCell>{approval.requested_by.email || "Unknown"}</TableCell>
                        <TableCell>
                          {approval.approved_by?.email || "Unknown"}
                        </TableCell>
                        <TableCell>
                          {approval.decided_at
                            ? formatDistanceToNow(new Date(approval.decided_at), { addSuffix: true })
                            : "N/A"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Approve Dialog */}
      <Dialog open={approveDialogOpen} onOpenChange={setApproveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve Action</DialogTitle>
            <DialogDescription>
              Enter the confirmation phrase to approve this high-risk action.
            </DialogDescription>
          </DialogHeader>
          {selectedApproval && (
            <div className="space-y-4">
              <div>
                <Label>Action Type</Label>
                <p className="text-sm font-medium">
                  {ACTION_LABELS[selectedApproval.action_type] || selectedApproval.action_type}
                </p>
              </div>
              <div>
                <Label>Confirmation Phrase</Label>
                <Input
                  value={confirmationPhrase}
                  onChange={(e) => setConfirmationPhrase(e.target.value)}
                  placeholder={CONFIRMATION_PHRASES[selectedApproval.action_type]}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Expected: <code>{CONFIRMATION_PHRASES[selectedApproval.action_type]}</code>
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setApproveDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleApprove}
              disabled={!confirmationPhrase.trim() || approveMutation.isPending}
            >
              {approveMutation.isPending ? "Approving..." : "Approve"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Approval Request</DialogTitle>
            <DialogDescription>
              Are you sure you want to reject this approval request?
            </DialogDescription>
          </DialogHeader>
          {selectedApproval && (
            <div className="space-y-2">
              <p className="text-sm">
                <strong>Action:</strong> {ACTION_LABELS[selectedApproval.action_type] || selectedApproval.action_type}
              </p>
              <p className="text-sm">
                <strong>Requested by:</strong> {selectedApproval.requested_by.email}
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={rejectMutation.isPending}
            >
              {rejectMutation.isPending ? "Rejecting..." : "Reject"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Request Dialog */}
      <Dialog open={requestDialogOpen} onOpenChange={setRequestDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Request Approval</DialogTitle>
            <DialogDescription>
              Request two-person approval for a high-risk action (production only)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Action Type</Label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={requestForm.action_type}
                onChange={(e) =>
                  setRequestForm({
                    ...requestForm,
                    action_type: e.target.value as ApprovalRequest["action_type"],
                    confirmation_phrase: CONFIRMATION_PHRASES[e.target.value] || "",
                  })
                }
              >
                {Object.keys(ACTION_LABELS).map((key) => (
                  <option key={key} value={key}>
                    {ACTION_LABELS[key]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Reason *</Label>
              <Input
                value={requestForm.reason}
                onChange={(e) => setRequestForm({ ...requestForm, reason: e.target.value })}
                placeholder="Explain why this action is needed"
              />
            </div>
            <div>
              <Label>Confirmation Phrase *</Label>
              <Input
                value={requestForm.confirmation_phrase}
                onChange={(e) =>
                  setRequestForm({ ...requestForm, confirmation_phrase: e.target.value })
                }
                placeholder={CONFIRMATION_PHRASES[requestForm.action_type || "PROFILE_SWITCH_PRIMARY"]}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Expected: <code>{CONFIRMATION_PHRASES[requestForm.action_type || "PROFILE_SWITCH_PRIMARY"]}</code>
              </p>
            </div>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This approval request will require a second admin to approve before the action can be executed.
              </AlertDescription>
            </Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRequestDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRequestSubmit}
              disabled={
                !requestForm.action_type ||
                !requestForm.reason ||
                !requestForm.confirmation_phrase ||
                requestMutation.isPending
              }
            >
              {requestMutation.isPending ? "Submitting..." : "Submit Request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
