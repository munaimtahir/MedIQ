"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { AlertTriangle, Database, Search, Zap } from "lucide-react";
import type { SearchResponse } from "@/lib/types/search";
import { RefObject } from "react";

interface SearchBarRowProps {
  q: string;
  onQueryChange: (q: string) => void;
  sort: "relevance" | "published_at_desc" | "updated_at_desc";
  onSortChange: (sort: "relevance" | "published_at_desc" | "updated_at_desc") => void;
  includeUnpublished: boolean;
  onIncludeUnpublishedChange: (include: boolean) => void;
  searchResult: SearchResponse | null;
  canIncludeUnpublished: boolean;
  searchInputRef?: RefObject<HTMLInputElement>;
}

export function SearchBarRow({
  q,
  onQueryChange,
  sort,
  onSortChange,
  includeUnpublished,
  onIncludeUnpublishedChange,
  searchResult,
  canIncludeUnpublished,
  searchInputRef,
}: SearchBarRowProps) {
  const isDegraded = searchResult?.engine === "postgres";
  const hasFallbackWarning =
    searchResult?.warnings.some((w) =>
      w.includes("elasticsearch_unreachable_fallback_postgres") ||
      w.includes("elasticsearch_disabled_env_fallback_postgres"),
    ) || false;
  const hasReadinessWarning =
    searchResult?.warnings.some((w) => w.includes("elasticsearch_not_ready") || w.includes("readiness_blocked")) ||
    false;

  return (
    <div className="space-y-4">
      {/* Search Input + Engine Status + Sort */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            ref={searchInputRef}
            value={q}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Search questions by stem, explanation, or tags... (Press / to focus)"
            className="pl-9"
          />
        </div>

        {/* Engine Pill with Tooltip */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2">
                {searchResult?.engine === "elasticsearch" ? (
                  <Badge variant="default" className="bg-green-600 cursor-help">
                    <Zap className="mr-1 h-3 w-3" />
                    Elasticsearch
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="cursor-help">
                    <Database className="mr-1 h-3 w-3" />
                    Postgres
                  </Badge>
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p className="text-xs max-w-xs">
                {searchResult?.engine === "elasticsearch"
                  ? "Full-text search with relevance ranking and complete facet counts"
                  : "Database fallback mode: limited facets and basic text matching"}
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Sort */}
        <Select value={sort} onValueChange={onSortChange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="relevance">Relevance</SelectItem>
            <SelectItem value="published_at_desc">Published (Newest)</SelectItem>
            <SelectItem value="updated_at_desc">Updated (Newest)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Include Unpublished Toggle */}
      {canIncludeUnpublished && (
        <div className="flex items-center space-x-2">
          <Switch
            id="include-unpublished"
            checked={includeUnpublished}
            onCheckedChange={onIncludeUnpublishedChange}
          />
          <Label htmlFor="include-unpublished" className="text-sm font-normal">
            Include unpublished questions
          </Label>
        </div>
      )}

      {/* Readiness Warning Banner */}
      {hasReadinessWarning && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-1">
              <div>
                <strong>Elasticsearch requested but not ready.</strong> Using Postgres fallback.
              </div>
              <div className="text-xs">
                {searchResult?.warnings
                  .filter((w) => w.includes("readiness_blocked"))
                  .map((w) => w.replace("readiness_blocked: ", ""))
                  .join("; ")}
              </div>
              <div className="text-xs mt-1">
                <a href="/admin/search" className="underline">
                  View readiness details
                </a>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Degraded Warning Banner (fallback) */}
      {hasFallbackWarning && !hasReadinessWarning && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Search degraded (Elasticsearch unavailable). Using Postgres fallback. Some features
            may be limited.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
