"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { Badge } from "@/components/ui/badge";
import { adminAPI } from "@/lib/api";
import { Question } from "@/lib/api";

export default function EditQuestionPage() {
  const params = useParams();
  const router = useRouter();
  const questionId = Number(params.id);
  const [question, setQuestion] = useState<Question | null>(null);
  const [formData, setFormData] = useState({
    question_text: "",
    options: ["", "", "", "", ""],
    correct_option_index: "",
    explanation: "",
    tags: "",
    difficulty: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adminAPI
      .getQuestion(questionId)
      .then((q) => {
        setQuestion(q);
        setFormData({
          question_text: q.question_text,
          options: q.options,
          correct_option_index: q.correct_option_index.toString(),
          explanation: q.explanation || "",
          tags: q.tags?.join(", ") || "",
          difficulty: q.difficulty || "",
        });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [questionId]);

  const handleOptionChange = (index: number, value: string) => {
    const newOptions = [...formData.options];
    newOptions[index] = value;
    setFormData({ ...formData, options: newOptions });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const tags = formData.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await adminAPI.updateQuestion(questionId, {
        question_text: formData.question_text,
        options: formData.options,
        correct_option_index: Number(formData.correct_option_index),
        explanation: formData.explanation || undefined,
        tags: tags.length > 0 ? tags : undefined,
        difficulty: formData.difficulty || undefined,
      });
      router.push("/admin/questions");
    } catch (error: any) {
      console.error("Failed to update question:", error);
      alert(error.message || "Failed to update question");
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    try {
      await adminAPI.publishQuestion(questionId);
      router.push("/admin/questions");
    } catch (error) {
      console.error("Failed to publish:", error);
      alert("Failed to publish question");
    }
  };

  const handleUnpublish = async () => {
    try {
      await adminAPI.unpublishQuestion(questionId);
      router.push("/admin/questions");
    } catch (error) {
      console.error("Failed to unpublish:", error);
      alert("Failed to unpublish question");
    }
  };

  if (loading) {
    return <div>Loading question...</div>;
  }

  if (!question) {
    return <div>Question not found</div>;
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" onClick={() => router.back()}>
            ← Back
          </Button>
          <h1 className="mt-4 text-3xl font-bold">Edit Question #{questionId}</h1>
        </div>
        <div className="flex gap-2">
          {question.is_published ? (
            <Badge variant="success">Published</Badge>
          ) : (
            <Badge variant="secondary">Draft</Badge>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Question Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Theme ID</Label>
            <Input value={question.theme_id} disabled />
          </div>

          <div className="space-y-2">
            <Label htmlFor="question_text">Question Text *</Label>
            <Textarea
              id="question_text"
              value={formData.question_text}
              onChange={(e) => setFormData({ ...formData, question_text: e.target.value })}
              rows={4}
            />
          </div>

          <div className="space-y-2">
            <Label>Options *</Label>
            {formData.options.map((option, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="w-6 font-medium">{String.fromCharCode(65 + idx)}.</span>
                <Input value={option} onChange={(e) => handleOptionChange(idx, e.target.value)} />
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <Label htmlFor="correct_option_index">Correct Answer *</Label>
            <Select
              value={formData.correct_option_index}
              onValueChange={(v) => setFormData({ ...formData, correct_option_index: v })}
            >
              <SelectTrigger id="correct_option_index">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {formData.options.map((_, idx) => (
                  <SelectItem key={idx} value={idx.toString()}>
                    {String.fromCharCode(65 + idx)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="explanation">Explanation</Label>
            <Textarea
              id="explanation"
              value={formData.explanation}
              onChange={(e) => setFormData({ ...formData, explanation: e.target.value })}
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tags">Tags</Label>
              <Input
                id="tags"
                value={formData.tags}
                onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="difficulty">Difficulty</Label>
              <Select
                value={formData.difficulty}
                onValueChange={(v) => setFormData({ ...formData, difficulty: v })}
              >
                <SelectTrigger id="difficulty">
                  <SelectValue placeholder="Select difficulty" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="easy">Easy</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="hard">Hard</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex gap-4">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </Button>
            {question.is_published ? (
              <Button variant="outline" onClick={handleUnpublish}>
                Unpublish
              </Button>
            ) : (
              <Button variant="default" onClick={handlePublish}>
                Publish
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
