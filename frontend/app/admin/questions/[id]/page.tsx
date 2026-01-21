"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { QuestionEditor } from "@/components/admin/questions/QuestionEditor";
import { WorkflowPanel } from "@/components/admin/questions/WorkflowPanel";
import { VersionHistory } from "@/components/admin/questions/VersionHistory";
import { adminQuestionsApi } from "@/lib/admin/questionsApi";
import type { QuestionOut, QuestionUpdate } from "@/lib/types/question-cms";
import { notify } from "@/lib/notify";
import { ArrowLeft, Save, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { ErrorState } from "@/components/status/ErrorState";
import { useUserStore } from "@/store/userStore";

export default function EditQuestionPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const questionId = params.id as string;
  const isReviewMode = searchParams.get("mode") === "review";

  const { user } = useUserStore();
  const userRole = user?.role || "STUDENT";

  const [question, setQuestion] = useState<QuestionOut | null>(null);
  const [formData, setFormData] = useState<QuestionUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Load question
  const loadQuestion = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminQuestionsApi.getQuestion(questionId);
      setQuestion(data);
    } catch (err) {
      console.error("Failed to load question:", err);
      setError(err instanceof Error ? err : new Error("Failed to load question"));
    } finally {
      setLoading(false);
    }
  }, [questionId]);

  useEffect(() => {
    loadQuestion();
  }, [loadQuestion]);

  // Track unsaved changes
  useEffect(() => {
    if (Object.keys(formData).length > 0) {
      setHasUnsavedChanges(true);
    }
  }, [formData]);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = "";
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasUnsavedChanges]);

  const handleSave = async () => {
    if (Object.keys(formData).length === 0) {
      notify.info("No Changes", "No changes to save");
      return;
    }

    setSaving(true);
    try {
      const updated = await adminQuestionsApi.updateQuestion(questionId, formData);
      setQuestion(updated);
      setFormData({});
      setHasUnsavedChanges(false);
      notify.success("Saved", "Question has been updated");
    } catch (error) {
      console.error("Failed to update question:", error);
      notify.error(
        "Save Failed",
        error instanceof Error ? error.message : "Failed to update question",
      );
    } finally {
      setSaving(false);
    }
  };

  // Workflow actions
  const handleSubmit = async () => {
    try {
      await adminQuestionsApi.submitQuestion(questionId);
      notify.success("Submitted", "Question has been submitted for review");
      loadQuestion();
    } catch (error) {
      notify.error(
        "Submit Failed",
        error instanceof Error ? error.message : "Failed to submit question",
      );
      throw error;
    }
  };

  const handleApprove = async () => {
    try {
      await adminQuestionsApi.approveQuestion(questionId);
      notify.success("Approved", "Question has been approved");
      loadQuestion();
    } catch (error) {
      notify.error(
        "Approve Failed",
        error instanceof Error ? error.message : "Failed to approve question",
      );
      throw error;
    }
  };

  const handleReject = async (reason: string) => {
    try {
      await adminQuestionsApi.rejectQuestion(questionId, reason);
      notify.success("Rejected", "Question has been rejected");
      loadQuestion();
    } catch (error) {
      notify.error(
        "Reject Failed",
        error instanceof Error ? error.message : "Failed to reject question",
      );
      throw error;
    }
  };

  const handlePublish = async () => {
    try {
      await adminQuestionsApi.publishQuestion(questionId);
      notify.success("Published", "Question is now published and available to students");
      loadQuestion();
    } catch (error) {
      notify.error(
        "Publish Failed",
        error instanceof Error ? error.message : "Failed to publish question",
      );
      throw error;
    }
  };

  const handleUnpublish = async () => {
    try {
      await adminQuestionsApi.unpublishQuestion(questionId);
      notify.success("Unpublished", "Question has been unpublished");
      loadQuestion();
    } catch (error) {
      notify.error(
        "Unpublish Failed",
        error instanceof Error ? error.message : "Failed to unpublish question",
      );
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold">Loading...</h1>
        </div>
        <SkeletonTable rows={10} cols={2} />
      </div>
    );
  }

  if (error || !question) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold">Error</h1>
        </div>
        <ErrorState
          variant="page"
          title="Failed to load question"
          description={error?.message || "Question not found"}
          actionLabel="Retry"
          onAction={loadQuestion}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">
                {isReviewMode ? "Review Question" : "Edit Question"}
              </h1>
              <Badge
                className={
                  question.status === "DRAFT"
                    ? "bg-gray-500"
                    : question.status === "IN_REVIEW"
                      ? "bg-yellow-500"
                      : question.status === "APPROVED"
                        ? "bg-blue-500"
                        : "bg-green-500"
                }
              >
                {question.status}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">ID: {question.id}</p>
          </div>
        </div>

        <div className="flex gap-2">
          {hasUnsavedChanges && (
            <Alert className="mr-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>You have unsaved changes</AlertDescription>
            </Alert>
          )}
          <Button onClick={handleSave} disabled={saving || !hasUnsavedChanges}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <QuestionEditor question={question} onChange={setFormData} />
        </div>

        <div className="space-y-6 lg:col-span-1">
          <WorkflowPanel
            status={question.status}
            userRole={userRole}
            onSubmit={handleSubmit}
            onApprove={handleApprove}
            onReject={handleReject}
            onPublish={handlePublish}
            onUnpublish={handleUnpublish}
            isLoading={saving}
          />

          <VersionHistory questionId={questionId} />
        </div>
      </div>

      {isReviewMode && (
        <Card className="bg-blue-50 dark:bg-blue-950">
          <CardHeader>
            <CardTitle className="text-base">Review Mode</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p>
              You are reviewing this question. Check all fields for completeness and accuracy, then
              use the workflow panel to approve or reject.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
