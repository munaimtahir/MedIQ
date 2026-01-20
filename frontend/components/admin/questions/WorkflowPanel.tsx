"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { QuestionStatus } from "@/lib/types/question-cms";
import { CheckCircle, XCircle, Send, Eye, EyeOff } from "lucide-react";

interface WorkflowPanelProps {
  status: QuestionStatus;
  userRole: "ADMIN" | "REVIEWER" | "STUDENT";
  onSubmit: () => Promise<void>;
  onApprove: () => Promise<void>;
  onReject: (reason: string) => Promise<void>;
  onPublish: () => Promise<void>;
  onUnpublish: () => Promise<void>;
  isLoading?: boolean;
}

const STATUS_COLORS: Record<QuestionStatus, string> = {
  DRAFT: "bg-gray-500",
  IN_REVIEW: "bg-yellow-500",
  APPROVED: "bg-blue-500",
  PUBLISHED: "bg-green-500",
};

const STATUS_LABELS: Record<QuestionStatus, string> = {
  DRAFT: "Draft",
  IN_REVIEW: "In Review",
  APPROVED: "Approved",
  PUBLISHED: "Published",
};

export function WorkflowPanel({
  status,
  userRole,
  onSubmit,
  onApprove,
  onReject,
  onPublish,
  onUnpublish,
  isLoading = false,
}: WorkflowPanelProps) {
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const handleRejectSubmit = async () => {
    if (!rejectReason.trim()) {
      return;
    }
    setActionLoading(true);
    try {
      await onReject(rejectReason);
      setRejectDialogOpen(false);
      setRejectReason("");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAction = async (action: () => Promise<void>) => {
    setActionLoading(true);
    try {
      await action();
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Workflow</CardTitle>
          <CardDescription>Manage question status and transitions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Current Status:</span>
            <Badge className={STATUS_COLORS[status]}>{STATUS_LABELS[status]}</Badge>
          </div>

          <div className="space-y-2">
            {/* DRAFT -> IN_REVIEW (Submit) */}
            {status === "DRAFT" && (userRole === "ADMIN" || userRole === "REVIEWER") && (
              <Button
                onClick={() => handleAction(onSubmit)}
                disabled={isLoading || actionLoading}
                className="w-full"
                variant="default"
              >
                <Send className="mr-2 h-4 w-4" />
                Submit for Review
              </Button>
            )}

            {/* IN_REVIEW -> APPROVED (Approve) */}
            {status === "IN_REVIEW" && (userRole === "ADMIN" || userRole === "REVIEWER") && (
              <div className="flex gap-2">
                <Button
                  onClick={() => handleAction(onApprove)}
                  disabled={isLoading || actionLoading}
                  className="flex-1"
                  variant="default"
                >
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Approve
                </Button>
                <Button
                  onClick={() => setRejectDialogOpen(true)}
                  disabled={isLoading || actionLoading}
                  className="flex-1"
                  variant="destructive"
                >
                  <XCircle className="mr-2 h-4 w-4" />
                  Reject
                </Button>
              </div>
            )}

            {/* APPROVED -> PUBLISHED (Publish, ADMIN only) */}
            {status === "APPROVED" && userRole === "ADMIN" && (
              <Button
                onClick={() => handleAction(onPublish)}
                disabled={isLoading || actionLoading}
                className="w-full"
                variant="default"
              >
                <Eye className="mr-2 h-4 w-4" />
                Publish
              </Button>
            )}

            {/* PUBLISHED -> APPROVED (Unpublish, ADMIN only) */}
            {status === "PUBLISHED" && userRole === "ADMIN" && (
              <Button
                onClick={() => handleAction(onUnpublish)}
                disabled={isLoading || actionLoading}
                className="w-full"
                variant="outline"
              >
                <EyeOff className="mr-2 h-4 w-4" />
                Unpublish
              </Button>
            )}

            {status === "PUBLISHED" && userRole !== "ADMIN" && (
              <p className="text-sm text-muted-foreground">
                Only admins can unpublish questions.
              </p>
            )}
          </div>

          {/* Workflow explanation */}
          <div className="mt-4 rounded-md bg-muted p-3 text-sm">
            <p className="font-medium mb-1">Workflow:</p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>Draft → Submit for Review</li>
              <li>In Review → Approve or Reject</li>
              <li>Approved → Publish (Admin only)</li>
              <li>Published → Unpublish (Admin only)</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Question</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejecting this question. The question will return to
              DRAFT status.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="reject_reason">Rejection Reason *</Label>
            <Textarea
              id="reject_reason"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={4}
              placeholder="Explain why this question is being rejected..."
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRejectDialogOpen(false);
                setRejectReason("");
              }}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRejectSubmit}
              disabled={!rejectReason.trim() || actionLoading}
            >
              {actionLoading ? "Rejecting..." : "Reject Question"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
