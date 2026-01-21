"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { QuestionListQuery, QuestionStatus } from "@/lib/types/question-cms";
import type { YearAdmin, BlockAdmin, ThemeAdmin } from "@/lib/api";
import { adminSyllabusAPI } from "@/lib/api";
import { Search, X } from "lucide-react";
import { useDebounce } from "@/lib/hooks/useDebounce";

interface QuestionFiltersProps {
  filters: QuestionListQuery;
  onChange: (filters: QuestionListQuery) => void;
  onReset: () => void;
}

const STATUS_OPTIONS: { value: QuestionStatus; label: string }[] = [
  { value: "DRAFT", label: "Draft" },
  { value: "IN_REVIEW", label: "In Review" },
  { value: "APPROVED", label: "Approved" },
  { value: "PUBLISHED", label: "Published" },
];

const DIFFICULTY_OPTIONS = [
  { value: "EASY", label: "Easy" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HARD", label: "Hard" },
];

const COGNITIVE_OPTIONS = [
  { value: "REMEMBER", label: "Remember" },
  { value: "UNDERSTAND", label: "Understand" },
  { value: "APPLY", label: "Apply" },
  { value: "ANALYZE", label: "Analyze" },
  { value: "EVALUATE", label: "Evaluate" },
  { value: "CREATE", label: "Create" },
];

export function QuestionFilters({ filters, onChange, onReset }: QuestionFiltersProps) {
  const [years, setYears] = useState<YearAdmin[]>([]);
  const [blocks, setBlocks] = useState<BlockAdmin[]>([]);
  const [themes, setThemes] = useState<ThemeAdmin[]>([]);

  const [searchInput, setSearchInput] = useState(filters.q || "");
  const debouncedSearch = useDebounce(searchInput, 500);

  // Load years on mount
  useEffect(() => {
    adminSyllabusAPI.getYears().then(setYears).catch(console.error);
  }, []);

  // Load blocks when year changes
  useEffect(() => {
    if (filters.year_id) {
      adminSyllabusAPI
        .getBlocks(filters.year_id)
        .then(setBlocks)
        .catch((err) => {
          console.error("Failed to load blocks:", err);
          setBlocks([]);
        });
    } else {
      setBlocks([]);
    }
  }, [filters.year_id]);

  // Load themes when block changes
  useEffect(() => {
    if (filters.block_id) {
      adminSyllabusAPI
        .getThemes(filters.block_id)
        .then(setThemes)
        .catch((err) => {
          console.error("Failed to load themes:", err);
          setThemes([]);
        });
    } else {
      setThemes([]);
    }
  }, [filters.block_id]);

  // Update filters when debounced search changes
  useEffect(() => {
    onChange({ ...filters, q: debouncedSearch || undefined });
  }, [debouncedSearch, filters, onChange]);

  const handleFilterChange = (key: keyof QuestionListQuery, value: string | number | undefined) => {
    onChange({ ...filters, [key]: value, page: 1 });
  };

  const handleYearChange = (yearId: string | undefined) => {
    onChange({
      ...filters,
      year_id: yearId ? Number(yearId) : undefined,
      block_id: undefined,
      theme_id: undefined,
      page: 1,
    });
  };

  const handleBlockChange = (blockId: string | undefined) => {
    onChange({
      ...filters,
      block_id: blockId ? Number(blockId) : undefined,
      theme_id: undefined,
      page: 1,
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Filters</CardTitle>
            <CardDescription>Filter and search questions</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onReset}>
            <X className="mr-2 h-4 w-4" />
            Reset
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search */}
        <div className="space-y-2">
          <Label htmlFor="search">Search</Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by stem text or ID..."
              className="pl-9"
            />
          </div>
        </div>

        {/* Status */}
        <div className="space-y-2">
          <Label htmlFor="status">Status</Label>
          <Select
            value={filters.status || ""}
            onValueChange={(v) => handleFilterChange("status", v || undefined)}
          >
            <SelectTrigger id="status">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All statuses</SelectItem>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Year → Block → Theme (Cascading) */}
        <div className="space-y-2">
          <Label htmlFor="year">Year</Label>
          <Select
            value={filters.year_id?.toString() || ""}
            onValueChange={(v) => handleYearChange(v || undefined)}
          >
            <SelectTrigger id="year">
              <SelectValue placeholder="All years" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All years</SelectItem>
              {years.map((year) => (
                <SelectItem key={year.id} value={year.id.toString()}>
                  {year.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="block">Block</Label>
          <Select
            value={filters.block_id?.toString() || ""}
            onValueChange={(v) => handleBlockChange(v || undefined)}
            disabled={!filters.year_id}
          >
            <SelectTrigger id="block">
              <SelectValue placeholder="All blocks" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All blocks</SelectItem>
              {blocks.map((block) => (
                <SelectItem key={block.id} value={block.id.toString()}>
                  {block.code} - {block.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="theme">Theme</Label>
          <Select
            value={filters.theme_id?.toString() || ""}
            onValueChange={(v) => handleFilterChange("theme_id", v ? Number(v) : undefined)}
            disabled={!filters.block_id}
          >
            <SelectTrigger id="theme">
              <SelectValue placeholder="All themes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All themes</SelectItem>
              {themes.map((theme) => (
                <SelectItem key={theme.id} value={theme.id.toString()}>
                  {theme.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Cognitive Level */}
        <div className="space-y-2">
          <Label htmlFor="cognitive">Cognitive Level</Label>
          <Select
            value={filters.cognitive_level || ""}
            onValueChange={(v) => handleFilterChange("cognitive_level", v || undefined)}
          >
            <SelectTrigger id="cognitive">
              <SelectValue placeholder="All levels" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All levels</SelectItem>
              {COGNITIVE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Difficulty */}
        <div className="space-y-2">
          <Label htmlFor="difficulty">Difficulty</Label>
          <Select
            value={filters.difficulty || ""}
            onValueChange={(v) => handleFilterChange("difficulty", v || undefined)}
          >
            <SelectTrigger id="difficulty">
              <SelectValue placeholder="All difficulties" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All difficulties</SelectItem>
              {DIFFICULTY_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
