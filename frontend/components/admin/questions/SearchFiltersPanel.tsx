"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { adminSyllabusAPI } from "@/lib/api";
import type { YearAdmin, BlockAdmin, ThemeAdmin } from "@/lib/api";
import type { SearchQueryParams, SearchResponse } from "@/lib/types/search";
import { X } from "lucide-react";

interface SearchFiltersPanelProps {
  filters: SearchQueryParams;
  onChange: (filters: SearchQueryParams) => void;
  onReset: () => void;
  searchResult: SearchResponse | null;
  userRole: string;
}

const COGNITIVE_OPTIONS = [
  { value: "REMEMBER", label: "Remember" },
  { value: "UNDERSTAND", label: "Understand" },
  { value: "APPLY", label: "Apply" },
  { value: "ANALYZE", label: "Analyze" },
  { value: "EVALUATE", label: "Evaluate" },
  { value: "CREATE", label: "Create" },
];

const DIFFICULTY_OPTIONS = [
  { value: "EASY", label: "Easy" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HARD", label: "Hard" },
];

const STATUS_OPTIONS = [
  { value: "DRAFT", label: "Draft" },
  { value: "IN_REVIEW", label: "In Review" },
  { value: "APPROVED", label: "Approved" },
  { value: "PUBLISHED", label: "Published" },
];

export function SearchFiltersPanel({
  filters,
  onChange,
  onReset,
  searchResult,
  userRole,
}: SearchFiltersPanelProps) {
  const [years, setYears] = useState<YearAdmin[]>([]);
  const [blocks, setBlocks] = useState<BlockAdmin[]>([]);
  const [themes, setThemes] = useState<ThemeAdmin[]>([]);

  // Load years on mount
  useEffect(() => {
    adminSyllabusAPI.getYears().then(setYears).catch(console.error);
  }, []);

  // Load blocks when year changes
  useEffect(() => {
    if (filters.year !== undefined && filters.year !== null) {
      // Find year by order_no (filters.year is order_no, not id)
      const year = years.find((y) => y.order_no === filters.year);
      if (year) {
        adminSyllabusAPI
          .getBlocks(year.id)
          .then(setBlocks)
          .catch((err) => {
            console.error("Failed to load blocks:", err);
            setBlocks([]);
          });
      } else {
        setBlocks([]);
      }
    } else {
      setBlocks([]);
    }
  }, [filters.year, years]);

  // Load themes when block changes
  useEffect(() => {
    if (filters.block_id) {
      const blockId = parseInt(filters.block_id);
      if (!isNaN(blockId)) {
        adminSyllabusAPI
          .getThemes(blockId)
          .then(setThemes)
          .catch((err) => {
            console.error("Failed to load themes:", err);
            setThemes([]);
          });
      } else {
        setThemes([]);
      }
    } else {
      setThemes([]);
    }
  }, [filters.block_id]);

  // Get facet counts
  const facets = searchResult?.facets || {
    year: [],
    block_id: [],
    theme_id: [],
    cognitive_level: [],
    difficulty_label: [],
    source_book: [],
    status: [],
  };

  const isDegraded = searchResult?.warnings.some((w) => w.includes("facets_degraded_postgres"));

  // Get allowed statuses based on role
  const allowedStatuses = useMemo(() => {
    if (userRole === "ADMIN") {
      return STATUS_OPTIONS;
    } else if (userRole === "REVIEWER") {
      // REVIEWER cannot see DRAFT
      return STATUS_OPTIONS.filter((s) => s.value !== "DRAFT");
    }
    return STATUS_OPTIONS.filter((s) => s.value === "PUBLISHED");
  }, [userRole]);

  // Helper to get facet count
  const getFacetCount = (facetKey: keyof typeof facets, value: string | number): number => {
    const facet = facets[facetKey];
    const item = facet.find((f) => f.value === value);
    return item?.count || 0;
  };

  // Helper to check if multi-select value is selected
  const isMultiSelected = (arr: string[] | undefined, value: string): boolean => {
    return arr?.includes(value) || false;
  };

  // Helper to toggle multi-select value
  const toggleMultiSelect = (
    key: keyof SearchQueryParams,
    value: string,
    current: string[] | undefined,
  ) => {
    const currentArr = current || [];
    const newArr = currentArr.includes(value)
      ? currentArr.filter((v) => v !== value)
      : [...currentArr, value];
    onChange({ ...filters, [key]: newArr.length > 0 ? newArr : undefined, page: 1 });
  };

  const handleYearChange = (yearOrder: string | undefined) => {
    onChange({
      ...filters,
      year: yearOrder ? parseInt(yearOrder) : undefined,
      block_id: undefined,
      theme_id: undefined,
      page: 1,
    });
  };

  const handleBlockChange = (blockId: string | undefined) => {
    onChange({
      ...filters,
      block_id: blockId,
      theme_id: undefined,
      page: 1,
    });
  };

  const handleThemeChange = (themeId: string | undefined) => {
    onChange({
      ...filters,
      theme_id: themeId,
      page: 1,
    });
  };

  // Get unique source books from facets
  const sourceBookOptions = useMemo(() => {
    const books = facets.source_book.map((f) => f.value as string);
    return [...new Set(books)].sort();
  }, [facets.source_book]);

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
        {/* Year (single) */}
        <div className="space-y-2">
          <Label htmlFor="year">Year</Label>
          <Select
            value={filters.year?.toString() || ""}
            onValueChange={(v) => handleYearChange(v || undefined)}
          >
            <SelectTrigger id="year">
              <SelectValue placeholder="All years" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All years</SelectItem>
              {years.map((year) => {
                const count = isDegraded ? null : getFacetCount("year", year.order_no);
                return (
                  <SelectItem key={year.id} value={year.order_no.toString()}>
                    {year.name}
                    {count !== null && count > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">({count})</span>
                    )}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>

        {/* Block (single, depends on Year) */}
        <div className="space-y-2">
          <Label htmlFor="block">Block</Label>
          <Select
            value={filters.block_id || ""}
            onValueChange={(v) => handleBlockChange(v || undefined)}
            disabled={!filters.year}
          >
            <SelectTrigger id="block">
              <SelectValue placeholder="All blocks" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All blocks</SelectItem>
              {blocks.map((block) => {
                const count = isDegraded ? null : getFacetCount("block_id", block.id.toString());
                return (
                  <SelectItem key={block.id} value={block.id.toString()}>
                    {block.code} - {block.name}
                    {count !== null && count > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">({count})</span>
                    )}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>

        {/* Theme (single, depends on Block) */}
        <div className="space-y-2">
          <Label htmlFor="theme">Theme</Label>
          <Select
            value={filters.theme_id || ""}
            onValueChange={(v) => handleThemeChange(v || undefined)}
            disabled={!filters.block_id}
          >
            <SelectTrigger id="theme">
              <SelectValue placeholder="All themes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All themes</SelectItem>
              {themes.map((theme) => {
                const count = isDegraded ? null : getFacetCount("theme_id", theme.id.toString());
                return (
                  <SelectItem key={theme.id} value={theme.id.toString()}>
                    {theme.title}
                    {count !== null && count > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">({count})</span>
                    )}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>

        {/* Cognitive Level (multi) */}
        <div className="space-y-2">
          <Label>Cognitive Level</Label>
          {isDegraded && (
            <p className="text-xs text-muted-foreground">Counts unavailable in fallback mode</p>
          )}
          <div className="space-y-2">
            {COGNITIVE_OPTIONS.map((opt) => {
              const count = isDegraded ? null : getFacetCount("cognitive_level", opt.value);
              return (
                <div key={opt.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`cognitive-${opt.value}`}
                    checked={isMultiSelected(filters.cognitive_level, opt.value)}
                    onCheckedChange={() => toggleMultiSelect("cognitive_level", opt.value, filters.cognitive_level)}
                  />
                  <Label
                    htmlFor={`cognitive-${opt.value}`}
                    className="text-sm font-normal cursor-pointer flex-1"
                  >
                    {opt.label}
                    {count !== null && count > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">({count})</span>
                    )}
                  </Label>
                </div>
              );
            })}
          </div>
        </div>

        {/* Difficulty (multi) */}
        <div className="space-y-2">
          <Label>Difficulty</Label>
          {isDegraded && (
            <p className="text-xs text-muted-foreground">Counts unavailable in fallback mode</p>
          )}
          <div className="space-y-2">
            {DIFFICULTY_OPTIONS.map((opt) => {
              const count = isDegraded ? null : getFacetCount("difficulty_label", opt.value);
              return (
                <div key={opt.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`difficulty-${opt.value}`}
                    checked={isMultiSelected(filters.difficulty_label, opt.value)}
                    onCheckedChange={() => toggleMultiSelect("difficulty_label", opt.value, filters.difficulty_label)}
                  />
                  <Label
                    htmlFor={`difficulty-${opt.value}`}
                    className="text-sm font-normal cursor-pointer flex-1"
                  >
                    {opt.label}
                    {count !== null && count > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">({count})</span>
                    )}
                  </Label>
                </div>
              );
            })}
          </div>
        </div>

        {/* Status (multi, role-aware) */}
        <div className="space-y-2">
          <Label>Status</Label>
          {isDegraded && (
            <p className="text-xs text-muted-foreground">Counts unavailable in fallback mode</p>
          )}
          <div className="space-y-2">
            {allowedStatuses.map((opt) => {
              const count = isDegraded ? null : getFacetCount("status", opt.value);
              return (
                <div key={opt.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`status-${opt.value}`}
                    checked={isMultiSelected(filters.status, opt.value)}
                    onCheckedChange={() => toggleMultiSelect("status", opt.value, filters.status)}
                  />
                  <Label
                    htmlFor={`status-${opt.value}`}
                    className="text-sm font-normal cursor-pointer flex-1"
                  >
                    {opt.label}
                    {count !== null && count > 0 && (
                      <span className="ml-2 text-xs text-muted-foreground">({count})</span>
                    )}
                  </Label>
                </div>
              );
            })}
          </div>
        </div>

        {/* Source Book (multi) */}
        <div className="space-y-2">
          <Label>Source Book</Label>
          {isDegraded && (
            <p className="text-xs text-muted-foreground">Counts unavailable in fallback mode</p>
          )}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {sourceBookOptions.length > 0 ? (
              sourceBookOptions.map((book) => {
                const count = isDegraded ? null : getFacetCount("source_book", book);
                return (
                  <div key={book} className="flex items-center space-x-2">
                    <Checkbox
                      id={`source-${book}`}
                      checked={isMultiSelected(filters.source_book, book)}
                      onCheckedChange={() => toggleMultiSelect("source_book", book, filters.source_book)}
                    />
                    <Label
                      htmlFor={`source-${book}`}
                      className="text-sm font-normal cursor-pointer flex-1 truncate"
                    >
                      {book}
                      {count !== null && count > 0 && (
                        <span className="ml-2 text-xs text-muted-foreground">({count})</span>
                      )}
                    </Label>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-muted-foreground">No source books available</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
