"use client";

import { usePendingApprovals, useApproveRequest, useRejectRequest } from "@/lib/admin/approvals/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle, CheckCircle2, XCircle, Clock } from "lucide-react";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatDistanceToNow } from "@/lib/dateUtils";

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

export function PendingApprovalsCard() {
  const { data, isLoading } = usePendingApprovals();
  const approveMutation = useApproveRequest();
  const rejectMutation = useRejectRequest();

  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<string | null>(null);
  const [confirmationPhrase, setConfirmationPhrase] = useState("");

  const pendingApprovals = data?.approvals.filter((a) => a.status === "PENDING") || [];

  const handleApproveClick = (requestId: string, actionType: string) => {
    setSelectedRequest(requestId);
    setConfirmationPhrase("");
    setApproveDialogOpen(true);
  };

  const handleApprove = () => {
    if (!selectedRequest) return;

    const approval = data?.approvals.find((a) => a.request_id === selectedRequest);
    if (!approval) return;

    const expectedPhrase = CONFIRMATION_PHRASES[approval.action_type];
    if (confirmationPhrase.trim().toUpperCase() !== expectedPhrase.toUpperCase()) {
      return; // Validation will be done by backend
    }

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
        },
      }
    );
  };

  const handleReject = (requestId: string) => {
    if (confirm("Are you sure you want to reject this approval request?")) {
      rejectMutation.mutate(requestId);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pending Approvals</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 bg-muted animate-pulse rounded" />
        </CardContent>
      </Card>
    );
  }

  if (pendingApprovals.length === 0) {
    return null; // Don't show card if no pending approvals
  }

  return (
    <>
      <Card className="border-orange-500">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            Pending Approvals ({pendingApprovals.length})
          </CardTitle>
          <CardDescription>
            High-risk actions require two-person approval in production
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {pendingApprovals.map((approval) => (
            <div
              key={approval.request_id}
              className="border rounded-lg p-4 space-y-3 bg-card"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{ACTION_LABELS[approval.action_type] || approval.action_type}</Badge>
                    <Badge variant="secondary">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Requested by: <strong>{approval.requested_by.email}</strong>
                  </p>
                  {approval.requested_action?.reason && (
                    <p className="text-sm">{approval.requested_action.reason}</p>
                  )}
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => handleApproveClick(approval.request_id, approval.action_type)}
                  disabled={approveMutation.isPending || rejectMutation.isPending}
                >
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleReject(approval.request_id)}
                  disabled={approveMutation.isPending || rejectMutation.isPending}
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Reject
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Dialog open={approveDialogOpen} onOpenChange={setApproveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve Action</DialogTitle>
            <DialogDescription>
              Enter the confirmation phrase to approve this high-risk action.
            </DialogDescription>
          </DialogHeader>
          {selectedRequest && (
            <>
              {(() => {
                const approval = data?.approvals.find((a) => a.request_id === selectedRequest);
                const expectedPhrase = approval
                  ? CONFIRMATION_PHRASES[approval.action_type]
                  : "";
                const isConfirmed =
                  confirmationPhrase.trim().toUpperCase() === expectedPhrase.toUpperCase();

                return (
                  <div className="space-y-4">
                    <div>
                      <Label>Confirmation Phrase</Label>
                      <Input
                        value={confirmationPhrase}
                        onChange={(e) => setConfirmationPhrase(e.target.value)}
                        placeholder={expectedPhrase}
                        className={isConfirmed ? "border-green-500" : ""}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Expected: <code className="text-xs">{expectedPhrase}</code>
                      </p>
                      {isConfirmed && (
                        <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          Confirmed
                        </p>
                      )}
                    </div>
                  </div>
                );
              })()}
            </>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setApproveDialogOpen(false);
                setSelectedRequest(null);
                setConfirmationPhrase("");
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleApprove}
              disabled={
                !selectedRequest ||
                !confirmationPhrase.trim() ||
                approveMutation.isPending
              }
            >
              {approveMutation.isPending ? "Approving..." : "Approve"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
