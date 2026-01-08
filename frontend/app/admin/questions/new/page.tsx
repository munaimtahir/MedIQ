"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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
import { adminAPI, syllabusAPI } from "@/lib/api";
import { Theme } from "@/lib/api";

export default function NewQuestionPage() {
  const router = useRouter();
  const [themes, setThemes] = useState<Theme[]>([]);
  const [formData, setFormData] = useState({
    theme_id: "",
    question_text: "",
    options: ["", "", "", "", ""],
    correct_option_index: "",
    explanation: "",
    tags: "",
    difficulty: "",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    syllabusAPI.getThemes().then(setThemes);
  }, []);

  const handleOptionChange = (index: number, value: string) => {
    const newOptions = [...formData.options];
    newOptions[index] = value;
    setFormData({ ...formData, options: newOptions });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const tags = formData.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await adminAPI.createQuestion({
        theme_id: Number(formData.theme_id),
        question_text: formData.question_text,
        options: formData.options,
        correct_option_index: Number(formData.correct_option_index),
        explanation: formData.explanation || undefined,
        tags: tags.length > 0 ? tags : undefined,
        difficulty: formData.difficulty || undefined,
      });
      router.push("/admin/questions");
    } catch (error: unknown) {
      console.error("Failed to create question:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to create question";
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <Button variant="ghost" onClick={() => router.back()}>
          ← Back
        </Button>
        <h1 className="mt-4 text-3xl font-bold">Create New Question</h1>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Question Details</CardTitle>
            <CardDescription>Fill in all required fields</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="theme">Theme *</Label>
              <Select
                value={formData.theme_id}
                onValueChange={(v) => setFormData({ ...formData, theme_id: v })}
              >
                <SelectTrigger id="theme">
                  <SelectValue placeholder="Select a theme" />
                </SelectTrigger>
                <SelectContent>
                  {themes.map((theme) => (
                    <SelectItem key={theme.id} value={theme.id.toString()}>
                      {theme.name} (Block {theme.block_id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="question_text">Question Text *</Label>
              <Textarea
                id="question_text"
                value={formData.question_text}
                onChange={(e) => setFormData({ ...formData, question_text: e.target.value })}
                rows={4}
                required
              />
            </div>

            <div className="space-y-2">
              <Label>Options * (exactly 5)</Label>
              {formData.options.map((option, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="w-6 font-medium">{String.fromCharCode(65 + idx)}.</span>
                  <Input
                    value={option}
                    onChange={(e) => handleOptionChange(idx, e.target.value)}
                    placeholder={`Option ${String.fromCharCode(65 + idx)}`}
                    required
                  />
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
                  <SelectValue placeholder="Select correct option" />
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
                <Label htmlFor="tags">Tags (comma-separated)</Label>
                <Input
                  id="tags"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="tag1, tag2, tag3"
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
              <Button type="submit" disabled={loading}>
                {loading ? "Creating..." : "Create Question"}
              </Button>
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
