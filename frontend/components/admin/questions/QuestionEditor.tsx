"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import type { QuestionOut, QuestionCreate, QuestionUpdate } from "@/lib/types/question-cms";
import type { YearAdmin, BlockAdmin, ThemeAdmin } from "@/lib/api";
import { adminSyllabusAPI } from "@/lib/api";

interface QuestionEditorProps {
  question?: QuestionOut;
  onChange: (data: QuestionCreate | QuestionUpdate) => void;
  errors?: Record<string, string>;
}

export function QuestionEditor({ question, onChange, errors }: QuestionEditorProps) {
  const [formData, setFormData] = useState<QuestionCreate | QuestionUpdate>({
    stem: question?.stem || "",
    option_a: question?.option_a || "",
    option_b: question?.option_b || "",
    option_c: question?.option_c || "",
    option_d: question?.option_d || "",
    option_e: question?.option_e || "",
    correct_index: question?.correct_index ?? null,
    explanation_md: question?.explanation_md || "",
    year_id: question?.year_id || null,
    block_id: question?.block_id || null,
    theme_id: question?.theme_id || null,
    cognitive_level: question?.cognitive_level || null,
    difficulty: question?.difficulty || null,
    source_book: question?.source_book || null,
    source_page: question?.source_page || null,
    source_ref: question?.source_ref || null,
  });

  // Syllabus data
  const [years, setYears] = useState<YearAdmin[]>([]);
  const [blocks, setBlocks] = useState<BlockAdmin[]>([]);
  const [themes, setThemes] = useState<ThemeAdmin[]>([]);

  // Load years on mount
  useEffect(() => {
    adminSyllabusAPI.getYears().then(setYears).catch(console.error);
  }, []);

  // Load blocks when year changes
  useEffect(() => {
    if (formData.year_id) {
      adminSyllabusAPI
        .getBlocks(formData.year_id)
        .then(setBlocks)
        .catch((err) => {
          console.error("Failed to load blocks:", err);
          setBlocks([]);
        });
    } else {
      setBlocks([]);
    }
  }, [formData.year_id]);

  // Load themes when block changes
  useEffect(() => {
    if (formData.block_id) {
      adminSyllabusAPI
        .getThemes(formData.block_id)
        .then(setThemes)
        .catch((err) => {
          console.error("Failed to load themes:", err);
          setThemes([]);
        });
    } else {
      setThemes([]);
    }
  }, [formData.block_id]);

  // Notify parent of changes
  useEffect(() => {
    onChange(formData);
  }, [formData, onChange]);

  const handleFieldChange = (field: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleYearChange = (yearId: string) => {
    setFormData((prev) => ({
      ...prev,
      year_id: Number(yearId),
      block_id: null,
      theme_id: null,
    }));
  };

  const handleBlockChange = (blockId: string) => {
    setFormData((prev) => ({
      ...prev,
      block_id: Number(blockId),
      theme_id: null,
    }));
  };

  return (
    <div className="space-y-6">
      {/* Question Content Card */}
      <Card>
        <CardHeader>
          <CardTitle>Question Content</CardTitle>
          <CardDescription>Enter the question stem and options (exactly 5)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="stem">Question Stem *</Label>
            <Textarea
              id="stem"
              value={formData.stem || ""}
              onChange={(e) => handleFieldChange("stem", e.target.value)}
              rows={6}
              placeholder="Enter the question text (supports Markdown and LaTeX)"
            />
            {errors?.stem && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errors.stem}</AlertDescription>
              </Alert>
            )}
          </div>

          <div className="space-y-2">
            <Label>Options (exactly 5) *</Label>
            {["option_a", "option_b", "option_c", "option_d", "option_e"].map((key, idx) => (
              <div key={key} className="flex items-center gap-2">
                <span className="w-6 font-medium">{String.fromCharCode(65 + idx)}.</span>
                <Input
                  value={(formData as Record<string, unknown>)[key] as string}
                  onChange={(e) => handleFieldChange(key, e.target.value)}
                  placeholder={`Option ${String.fromCharCode(65 + idx)}`}
                />
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <Label htmlFor="correct_index">Correct Answer *</Label>
            <Select
              value={formData.correct_index?.toString() || ""}
              onValueChange={(v) => handleFieldChange("correct_index", Number(v))}
            >
              <SelectTrigger id="correct_index">
                <SelectValue placeholder="Select correct option" />
              </SelectTrigger>
              <SelectContent>
                {[0, 1, 2, 3, 4].map((idx) => (
                  <SelectItem key={idx} value={idx.toString()}>
                    {String.fromCharCode(65 + idx)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Explanation Card */}
      <Card>
        <CardHeader>
          <CardTitle>Explanation</CardTitle>
          <CardDescription>
            Provide a detailed explanation (supports Markdown and LaTeX)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="explanation_md">Explanation</Label>
            <Textarea
              id="explanation_md"
              value={formData.explanation_md || ""}
              onChange={(e) => handleFieldChange("explanation_md", e.target.value)}
              rows={6}
              placeholder="Explain the correct answer and why other options are incorrect"
            />
          </div>
        </CardContent>
      </Card>

      {/* Tagging Card */}
      <Card>
        <CardHeader>
          <CardTitle>Tagging & Classification</CardTitle>
          <CardDescription>Assign year, block, theme, and metadata tags</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="year">Year *</Label>
              <Select value={formData.year_id?.toString() || ""} onValueChange={handleYearChange}>
                <SelectTrigger id="year">
                  <SelectValue placeholder="Select year" />
                </SelectTrigger>
                <SelectContent>
                  {years.map((year) => (
                    <SelectItem key={year.id} value={year.id.toString()}>
                      {year.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="block">Block *</Label>
              <Select
                value={formData.block_id?.toString() || ""}
                onValueChange={handleBlockChange}
                disabled={!formData.year_id}
              >
                <SelectTrigger id="block">
                  <SelectValue placeholder="Select block" />
                </SelectTrigger>
                <SelectContent>
                  {blocks.map((block) => (
                    <SelectItem key={block.id} value={block.id.toString()}>
                      {block.code} - {block.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="theme">Theme *</Label>
              <Select
                value={formData.theme_id?.toString() || ""}
                onValueChange={(v) => handleFieldChange("theme_id", Number(v))}
                disabled={!formData.block_id}
              >
                <SelectTrigger id="theme">
                  <SelectValue placeholder="Select theme" />
                </SelectTrigger>
                <SelectContent>
                  {themes.map((theme) => (
                    <SelectItem key={theme.id} value={theme.id.toString()}>
                      {theme.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="cognitive_level">Cognitive Level</Label>
              <Select
                value={formData.cognitive_level || ""}
                onValueChange={(v) => handleFieldChange("cognitive_level", v)}
              >
                <SelectTrigger id="cognitive_level">
                  <SelectValue placeholder="Select cognitive level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="REMEMBER">Remember</SelectItem>
                  <SelectItem value="UNDERSTAND">Understand</SelectItem>
                  <SelectItem value="APPLY">Apply</SelectItem>
                  <SelectItem value="ANALYZE">Analyze</SelectItem>
                  <SelectItem value="EVALUATE">Evaluate</SelectItem>
                  <SelectItem value="CREATE">Create</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="difficulty">Difficulty</Label>
              <Select
                value={formData.difficulty || ""}
                onValueChange={(v) => handleFieldChange("difficulty", v)}
              >
                <SelectTrigger id="difficulty">
                  <SelectValue placeholder="Select difficulty" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="EASY">Easy</SelectItem>
                  <SelectItem value="MEDIUM">Medium</SelectItem>
                  <SelectItem value="HARD">Hard</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Source Anchoring Card */}
      <Card>
        <CardHeader>
          <CardTitle>Source Anchoring</CardTitle>
          <CardDescription>Reference the source material</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="source_book">Source Book</Label>
              <Input
                id="source_book"
                value={formData.source_book || ""}
                onChange={(e) => handleFieldChange("source_book", e.target.value)}
                placeholder="e.g., Harrison's Principles"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="source_page">Page(s)</Label>
              <Input
                id="source_page"
                value={formData.source_page || ""}
                onChange={(e) => handleFieldChange("source_page", e.target.value)}
                placeholder="e.g., p. 123-125"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="source_ref">Reference ID</Label>
              <Input
                id="source_ref"
                value={formData.source_ref || ""}
                onChange={(e) => handleFieldChange("source_ref", e.target.value)}
                placeholder="e.g., REF-2024-001"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
