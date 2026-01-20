"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { QuestionEditor } from "@/components/admin/questions/QuestionEditor";
import { adminQuestionsApi } from "@/lib/admin/questionsApi";
import type { QuestionCreate } from "@/lib/types/question-cms";
import { notify } from "@/lib/notify";
import { ArrowLeft, Save } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

export default function NewQuestionPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<QuestionCreate>({});
  const [saving, setSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateDraft = (): boolean => {
    const errors: Record<string, string> = {};

    // For draft, only require minimal fields
    if (!formData.stem || formData.stem.trim() === "") {
      errors.stem = "Question stem is required";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveDraft = async () => {
    if (!validateDraft()) {
      notify.error("Validation Error", "Please fix the errors before saving");
      return;
    }

    setSaving(true);
    try {
      const created = await adminQuestionsApi.createQuestion(formData);
      notify.success("Draft Created", "Question has been saved as draft");
      router.push(`/admin/questions/${created.id}`);
    } catch (error) {
      console.error("Failed to create question:", error);
      notify.error(
        "Create Failed",
        error instanceof Error ? error.message : "Failed to create question",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Create New Question</h1>
            <p className="text-muted-foreground">Start with a draft and refine later</p>
          </div>
        </div>
      </div>

      {Object.keys(validationErrors).length > 0 && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please fix validation errors before saving: {Object.values(validationErrors).join(", ")}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>New Question (Draft)</CardTitle>
          <CardDescription>
            Fill in the question details. You can save as draft with minimal information and
            complete it later.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <QuestionEditor
            onChange={setFormData}
            errors={validationErrors}
          />

          <div className="mt-6 flex gap-4 justify-end border-t pt-6">
            <Button variant="outline" onClick={() => router.back()} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={handleSaveDraft} disabled={saving}>
              <Save className="mr-2 h-4 w-4" />
              {saving ? "Saving..." : "Save as Draft"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-base">Tips for Creating Questions</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <ul className="list-disc list-inside space-y-1 text-muted-foreground">
            <li>Start with a clear, concise question stem</li>
            <li>Provide exactly 5 options (A-E)</li>
            <li>Mark the correct answer</li>
            <li>Add a detailed explanation (helpful for students)</li>
            <li>Tag with Year, Block, and Theme for organization</li>
            <li>Reference source materials when available</li>
            <li>You can save as draft now and complete required fields before submitting for review</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
