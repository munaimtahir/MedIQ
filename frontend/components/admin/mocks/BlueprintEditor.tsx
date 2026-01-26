"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { X, Plus } from "lucide-react";
import type { MockBlueprint, MockBlueprintConfig } from "@/lib/api/adminMocks";
import { adminMocksAPI } from "@/lib/api/adminMocks";
import { notify } from "@/lib/notify";
import { useUserStore } from "@/store/userStore";

interface BlueprintEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  blueprint: MockBlueprint | null;
  onSave: () => void;
}

const defaultConfig: MockBlueprintConfig = {
  coverage: {
    mode: "counts",
    items: [],
  },
  difficulty_mix: { easy: 0.3, medium: 0.5, hard: 0.2 },
  cognitive_mix: { C1: 0.2, C2: 0.6, C3: 0.2 },
  tag_constraints: {
    must_include: {},
    must_exclude: {},
  },
  source_constraints: {},
  anti_repeat_policy: { avoid_days: 30, avoid_last_n: 0 },
  selection_policy: { type: "random_weighted" },
};

export function BlueprintEditor({ open, onOpenChange, blueprint, onSave }: BlueprintEditorProps) {
  const [title, setTitle] = useState("");
  const [year, setYear] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(25);
  const [durationMinutes, setDurationMinutes] = useState(120);
  const [mode, setMode] = useState<"EXAM" | "TUTOR">("EXAM");
  const [config, setConfig] = useState<MockBlueprintConfig>(defaultConfig);
  const [isSaving, setIsSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const userRole = useUserStore((state) => state.user?.role);
  const isAdmin = userRole === "ADMIN";

  useEffect(() => {
    if (blueprint) {
      setTitle(blueprint.title);
      setYear(blueprint.year);
      setTotalQuestions(blueprint.total_questions);
      setDurationMinutes(blueprint.duration_minutes);
      setMode(blueprint.mode);
      setConfig(blueprint.config);
    } else {
      setTitle("");
      setYear(1);
      setTotalQuestions(25);
      setDurationMinutes(120);
      setMode("EXAM");
      setConfig(defaultConfig);
    }
    setValidationErrors({});
  }, [blueprint, open]);

  const validateConfig = (): boolean => {
    const errors: Record<string, string> = {};

    // Validate coverage items
    if (config.coverage.items.length === 0) {
      errors.coverage = "At least one coverage item is required";
    }

    if (config.coverage.mode === "counts") {
      const totalCount = config.coverage.items.reduce(
        (sum, item) => sum + ("count" in item ? item.count : 0),
        0,
      );
      if (totalCount !== totalQuestions) {
        errors.coverage = `Total counts (${totalCount}) must equal total questions (${totalQuestions})`;
      }
    } else {
      const totalWeight = config.coverage.items.reduce(
        (sum, item) => sum + ("weight" in item ? item.weight : 0),
        0,
      );
      if (Math.abs(totalWeight - 1.0) > 0.01) {
        errors.coverage = `Total weights (${totalWeight.toFixed(2)}) must equal 1.0`;
      }
    }

    // Validate difficulty mix
    const difficultySum = config.difficulty_mix.easy + config.difficulty_mix.medium + config.difficulty_mix.hard;
    if (Math.abs(difficultySum - 1.0) > 0.01) {
      errors.difficulty = `Difficulty mix must sum to 1.0 (got ${difficultySum.toFixed(2)})`;
    }

    // Validate cognitive mix
    const cognitiveSum = config.cognitive_mix.C1 + config.cognitive_mix.C2 + config.cognitive_mix.C3;
    if (Math.abs(cognitiveSum - 1.0) > 0.01) {
      errors.cognitive = `Cognitive mix must sum to 1.0 (got ${cognitiveSum.toFixed(2)})`;
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSave = async () => {
    if (!validateConfig()) {
      notify.error("Validation failed", "Please fix the errors before saving");
      return;
    }

    setIsSaving(true);
    try {
      if (blueprint) {
        await adminMocksAPI.updateBlueprint(blueprint.id, {
          title,
          total_questions: totalQuestions,
          duration_minutes: durationMinutes,
          config,
        });
        notify.success("Blueprint updated", `"${title}" has been updated`);
      } else {
        await adminMocksAPI.createBlueprint({
          title,
          year,
          total_questions: totalQuestions,
          duration_minutes: durationMinutes,
          mode,
          config,
        });
        notify.success("Blueprint created", `"${title}" has been created`);
      }
      onSave();
      onOpenChange(false);
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to save blueprint", err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const addCoverageItem = () => {
    setConfig({
      ...config,
      coverage: {
        ...config.coverage,
        items: [
          ...config.coverage.items,
          config.coverage.mode === "counts"
            ? { theme_id: "", count: 0 }
            : { theme_id: "", weight: 0 },
        ],
      },
    });
  };

  const removeCoverageItem = (index: number) => {
    setConfig({
      ...config,
      coverage: {
        ...config.coverage,
        items: config.coverage.items.filter((_, i) => i !== index),
      },
    });
  };

  const updateCoverageItem = (index: number, field: string, value: string | number) => {
    const items = [...config.coverage.items];
    items[index] = { ...items[index], [field]: value };
    setConfig({
      ...config,
      coverage: { ...config.coverage, items },
    });
  };

  const updateDifficultyMix = (key: "easy" | "medium" | "hard", value: number[]) => {
    const newValue = value[0];
    const otherKeys = (["easy", "medium", "hard"] as const).filter((k) => k !== key);
    const otherSum = otherKeys.reduce((sum, k) => sum + config.difficulty_mix[k], 0);
    const maxOther = Math.min(1.0 - newValue, 1.0);
    const adjustedSum = Math.min(otherSum, maxOther);
    const scale = adjustedSum > 0 ? maxOther / otherSum : 1;

    setConfig({
      ...config,
      difficulty_mix: {
        ...config.difficulty_mix,
        [key]: newValue,
        ...Object.fromEntries(
          otherKeys.map((k) => [k, config.difficulty_mix[k] * scale]),
        ),
      },
    });
  };

  const updateCognitiveMix = (key: "C1" | "C2" | "C3", value: number[]) => {
    const newValue = value[0];
    const otherKeys = (["C1", "C2", "C3"] as const).filter((k) => k !== key);
    const otherSum = otherKeys.reduce((sum, k) => sum + config.cognitive_mix[k], 0);
    const maxOther = Math.min(1.0 - newValue, 1.0);
    const adjustedSum = Math.min(otherSum, maxOther);
    const scale = adjustedSum > 0 ? maxOther / otherSum : 1;

    setConfig({
      ...config,
      cognitive_mix: {
        ...config.cognitive_mix,
        [key]: newValue,
        ...Object.fromEntries(
          otherKeys.map((k) => [k, config.cognitive_mix[k] * scale]),
        ),
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{blueprint ? "Edit Blueprint" : "Create Blueprint"}</DialogTitle>
          <DialogDescription>
            Configure the blueprint settings and question selection criteria
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="basic" className="space-y-4">
          <TabsList>
            <TabsTrigger value="basic">Basic</TabsTrigger>
            <TabsTrigger value="coverage">Coverage</TabsTrigger>
            <TabsTrigger value="mix">Mix</TabsTrigger>
            <TabsTrigger value="constraints">Constraints</TabsTrigger>
            <TabsTrigger value="preview">JSON Preview</TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title *</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Mock Exam 2024"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="year">Year *</Label>
                <Input
                  id="year"
                  type="number"
                  min="1"
                  max="4"
                  value={year}
                  onChange={(e) => setYear(parseInt(e.target.value) || 1)}
                  disabled={!!blueprint}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="total_questions">Total Questions *</Label>
                <Input
                  id="total_questions"
                  type="number"
                  min="1"
                  max="300"
                  value={totalQuestions}
                  onChange={(e) => setTotalQuestions(parseInt(e.target.value) || 1)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration">Duration (minutes) *</Label>
                <Input
                  id="duration"
                  type="number"
                  min="1"
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 1)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mode">Mode *</Label>
                <select
                  id="mode"
                  value={mode}
                  onChange={(e) => setMode(e.target.value as "EXAM" | "TUTOR")}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="EXAM">EXAM</option>
                  <option value="TUTOR">TUTOR</option>
                </select>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="coverage" className="space-y-4">
            <div className="space-y-2">
              <Label>Coverage Mode</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={config.coverage.mode === "counts" ? "default" : "outline"}
                  onClick={() =>
                    setConfig({
                      ...config,
                      coverage: {
                        mode: "counts",
                        items: [],
                      },
                    })
                  }
                >
                  Counts
                </Button>
                <Button
                  type="button"
                  variant={config.coverage.mode === "weights" ? "default" : "outline"}
                  onClick={() =>
                    setConfig({
                      ...config,
                      coverage: {
                        mode: "weights",
                        items: [],
                      },
                    })
                  }
                >
                  Weights
                </Button>
              </div>
            </div>

            {validationErrors.coverage && (
              <div className="text-sm text-destructive">{validationErrors.coverage}</div>
            )}

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Coverage Items</Label>
                <Button variant="outline" size="sm" onClick={addCoverageItem}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Item
                </Button>
              </div>
              <div className="space-y-2">
                {config.coverage.items.map((item, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Input
                      placeholder="Theme ID"
                      value={item.theme_id}
                      onChange={(e) => updateCoverageItem(index, "theme_id", e.target.value)}
                      className="flex-1"
                    />
                    {config.coverage.mode === "counts" ? (
                      <Input
                        type="number"
                        min="0"
                        placeholder="Count"
                        value={"count" in item ? item.count : 0}
                        onChange={(e) =>
                          updateCoverageItem(index, "count", parseInt(e.target.value) || 0)
                        }
                        className="w-24"
                      />
                    ) : (
                      <Input
                        type="number"
                        min="0"
                        max="1"
                        step="0.01"
                        placeholder="Weight"
                        value={"weight" in item ? item.weight : 0}
                        onChange={(e) =>
                          updateCoverageItem(index, "weight", parseFloat(e.target.value) || 0)
                        }
                        className="w-24"
                      />
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeCoverageItem(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="mix" className="space-y-6">
            <div className="space-y-4">
              <div>
                <Label>Difficulty Mix</Label>
                {validationErrors.difficulty && (
                  <div className="text-sm text-destructive">{validationErrors.difficulty}</div>
                )}
                <div className="grid grid-cols-3 gap-4 mt-2">
                  <div className="space-y-2">
                    <Label className="text-sm">Easy</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={config.difficulty_mix.easy}
                      onChange={(e) => updateDifficultyMix("easy", [parseFloat(e.target.value) || 0])}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm">Medium</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={config.difficulty_mix.medium}
                      onChange={(e) => updateDifficultyMix("medium", [parseFloat(e.target.value) || 0])}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm">Hard</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={config.difficulty_mix.hard}
                      onChange={(e) => updateDifficultyMix("hard", [parseFloat(e.target.value) || 0])}
                    />
                  </div>
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  Sum: {(config.difficulty_mix.easy + config.difficulty_mix.medium + config.difficulty_mix.hard).toFixed(2)}
                </div>
              </div>

              <div>
                <Label>Cognitive Mix</Label>
                {validationErrors.cognitive && (
                  <div className="text-sm text-destructive">{validationErrors.cognitive}</div>
                )}
                <div className="grid grid-cols-3 gap-4 mt-2">
                  <div className="space-y-2">
                    <Label className="text-sm">C1</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={config.cognitive_mix.C1}
                      onChange={(e) => updateCognitiveMix("C1", [parseFloat(e.target.value) || 0])}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm">C2</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={config.cognitive_mix.C2}
                      onChange={(e) => updateCognitiveMix("C2", [parseFloat(e.target.value) || 0])}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm">C3</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={config.cognitive_mix.C3}
                      onChange={(e) => updateCognitiveMix("C3", [parseFloat(e.target.value) || 0])}
                    />
                  </div>
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  Sum: {(config.cognitive_mix.C1 + config.cognitive_mix.C2 + config.cognitive_mix.C3).toFixed(2)}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="constraints" className="space-y-4">
            <div className="space-y-2">
              <Label>Must Exclude Question IDs</Label>
              <Textarea
                placeholder="One question ID per line"
                value={config.tag_constraints.must_exclude.question_ids?.join("\n") || ""}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    tag_constraints: {
                      ...config.tag_constraints,
                      must_exclude: {
                        ...config.tag_constraints.must_exclude,
                        question_ids: e.target.value
                          .split("\n")
                          .map((id) => id.trim())
                          .filter((id) => id.length > 0),
                      },
                    },
                  })
                }
                rows={4}
              />
            </div>

            <div className="space-y-2">
              <Label>Anti-Repeat: Avoid Days</Label>
              <Input
                type="number"
                min="0"
                value={config.anti_repeat_policy.avoid_days}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    anti_repeat_policy: {
                      ...config.anti_repeat_policy,
                      avoid_days: parseInt(e.target.value) || 0,
                    },
                  })
                }
              />
            </div>
          </TabsContent>

          <TabsContent value="preview" className="space-y-4">
            <Label>Configuration JSON</Label>
            <pre className="rounded-md border bg-muted p-4 text-xs overflow-auto max-h-96">
              {JSON.stringify(
                {
                  title,
                  year,
                  total_questions: totalQuestions,
                  duration_minutes: durationMinutes,
                  mode,
                  config,
                },
                null,
                2,
              )}
            </pre>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : blueprint ? "Update" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
