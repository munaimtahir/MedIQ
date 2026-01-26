"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { Label } from "@/components/ui/label";
import { SearchFiltersPanel } from "@/components/admin/questions/SearchFiltersPanel";
import { SearchBarRow } from "@/components/admin/questions/SearchBarRow";
import { SearchResultsTable } from "@/components/admin/questions/SearchResultsTable";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { adminSearchApi } from "@/lib/admin/searchApi";
import type { SearchQueryParams, SearchResponse, SearchMetaResponse } from "@/lib/types/search";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { useUserStore } from "@/store/userStore";
import {
  saveScrollPosition,
  restoreScrollPosition,
  saveLastOpenedQuestion,
  getLastOpenedQuestion,
} from "@/lib/admin/questions/scrollPreservation";
import { FileQuestion, Plus } from "lucide-react";

export default function QuestionsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const user = useUserStore((state) => state.user);

  // Parse URL params into state
  const parseURLParams = useCallback((): SearchQueryParams => {
    const params: SearchQueryParams = {
      page: 1,
      page_size: 25,
      sort: "relevance",
    };

    const q = searchParams.get("q");
    const year = searchParams.get("year");
    const block_id = searchParams.get("block_id");
    const theme_id = searchParams.get("theme_id");
    const topic_id = searchParams.get("topic_id");
    const concept_id = searchParams.getAll("concept_id");
    const cognitive_level = searchParams.getAll("cognitive_level");
    const difficulty_label = searchParams.getAll("difficulty_label");
    const source_book = searchParams.getAll("source_book");
    const status = searchParams.getAll("status");
    const include_unpublished = searchParams.get("include_unpublished");
    const sort = searchParams.get("sort");
    const page = searchParams.get("page");
    const page_size = searchParams.get("page_size");

    if (q) params.q = q;
    if (year) params.year = parseInt(year);
    if (block_id) params.block_id = block_id;
    if (theme_id) params.theme_id = theme_id;
    if (topic_id) params.topic_id = topic_id;
    if (concept_id.length > 0) params.concept_id = concept_id;
    if (cognitive_level.length > 0) params.cognitive_level = cognitive_level;
    if (difficulty_label.length > 0) params.difficulty_label = difficulty_label;
    if (source_book.length > 0) params.source_book = source_book;
    if (status.length > 0) params.status = status;
    if (include_unpublished === "true") params.include_unpublished = true;
    if (sort) params.sort = sort as SearchQueryParams["sort"];
    if (page) params.page = parseInt(page);
    if (page_size) params.page_size = parseInt(page_size);

    return params;
  }, [searchParams]);

  const [filters, setFilters] = useState<SearchQueryParams>(parseURLParams);
  const [searchInput, setSearchInput] = useState(filters.q || "");
  const debouncedQuery = useDebounce(searchInput, 300);

  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [previousSearchResult, setPreviousSearchResult] = useState<SearchResponse | null>(null);
  const [searchMeta, setSearchMeta] = useState<SearchMetaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);
  const [highlightedQuestionId, setHighlightedQuestionId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load search metadata on mount
  useEffect(() => {
    adminSearchApi
      .getSearchMeta()
      .then(setSearchMeta)
      .catch((err) => console.error("Failed to load search metadata:", err));
  }, []);

  // Update URL when filters change
  const updateURL = useCallback(
    (newFilters: SearchQueryParams) => {
      const params = new URLSearchParams();

      if (newFilters.q) params.set("q", newFilters.q);
      if (newFilters.year !== undefined) params.set("year", newFilters.year.toString());
      if (newFilters.block_id) params.set("block_id", newFilters.block_id);
      if (newFilters.theme_id) params.set("theme_id", newFilters.theme_id);
      if (newFilters.topic_id) params.set("topic_id", newFilters.topic_id);
      if (newFilters.concept_id && newFilters.concept_id.length > 0) {
        newFilters.concept_id.forEach((id) => params.append("concept_id", id));
      }
      if (newFilters.cognitive_level && newFilters.cognitive_level.length > 0) {
        newFilters.cognitive_level.forEach((level) => params.append("cognitive_level", level));
      }
      if (newFilters.difficulty_label && newFilters.difficulty_label.length > 0) {
        newFilters.difficulty_label.forEach((diff) => params.append("difficulty_label", diff));
      }
      if (newFilters.source_book && newFilters.source_book.length > 0) {
        newFilters.source_book.forEach((book) => params.append("source_book", book));
      }
      if (newFilters.status && newFilters.status.length > 0) {
        newFilters.status.forEach((s) => params.append("status", s));
      }
      if (newFilters.include_unpublished) params.set("include_unpublished", "true");
      if (newFilters.sort) params.set("sort", newFilters.sort);
      if (newFilters.page && newFilters.page > 1) params.set("page", newFilters.page.toString());
      if (newFilters.page_size && newFilters.page_size !== 25)
        params.set("page_size", newFilters.page_size.toString());

      const queryString = params.toString();
      router.replace(`/admin/questions${queryString ? `?${queryString}` : ""}`, { scroll: false });
    },
    [router],
  );

  // Sync URL params to state when URL changes
  useEffect(() => {
    const newFilters = parseURLParams();
    setFilters(newFilters);
    setSearchInput(newFilters.q || "");
  }, [searchParams.toString()]); // Use toString() to avoid object reference issues

  // Update URL when debounced query changes
  const prevDebouncedQuery = useRef<string | undefined>(undefined);
  useEffect(() => {
    const currentQ = filters.q || "";
    // Only update if debounced value changed and differs from current filter
    if (debouncedQuery !== prevDebouncedQuery.current && debouncedQuery !== currentQ) {
      prevDebouncedQuery.current = debouncedQuery;
      updateURL({ ...filters, q: debouncedQuery || undefined, page: 1 });
    }
  }, [debouncedQuery, filters, updateURL]);

  // Load search results with caching
  const loadSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    // Keep previous data while loading
    setPreviousSearchResult((prev) => searchResult || prev);
    try {
      const startTime = performance.now();
      const data = await adminSearchApi.searchQuestions(filters);
      const latency = Math.round(performance.now() - startTime);
      setSearchResult(data);
      setPreviousSearchResult(null); // Clear previous after successful load

      // Prefetch next page if it exists
      const currentPage = filters.page || 1;
      const pageSize = filters.page_size || 25;
      const totalPages = Math.ceil(data.total / pageSize);
      if (currentPage < totalPages) {
        // Prefetch in background (don't await)
        adminSearchApi
          .searchQuestions({ ...filters, page: currentPage + 1 })
          .catch(() => {
            // Silently fail - prefetch is best effort
          });
      }
    } catch (err) {
      console.error("Failed to search questions:", err);
      setError(err instanceof Error ? err : new Error("Failed to search questions"));
      // Restore previous data on error
      setPreviousSearchResult((prev) => prev);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Load search when filters change
  useEffect(() => {
    loadSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  // Restore scroll position on mount
  useEffect(() => {
    const savedScroll = restoreScrollPosition(searchParams);
    if (savedScroll !== null && containerRef.current) {
      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo({ top: savedScroll, behavior: "auto" });
        });
      });
    }

    // Restore highlighted question
    const lastOpened = getLastOpenedQuestion(searchParams);
    if (lastOpened) {
      setHighlightedQuestionId(lastOpened);
      // Clear highlight after a delay
      setTimeout(() => setHighlightedQuestionId(null), 3000);
    }
  }, [searchParams]);

  // Save scroll position on unmount
  useEffect(() => {
    return () => {
      saveScrollPosition(searchParams, window.scrollY);
    };
  }, [searchParams]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Focus search on "/"
      if (e.key === "/" && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      // Escape to blur search
      if (e.key === "Escape" && document.activeElement === searchInputRef.current) {
        searchInputRef.current?.blur();
        return;
      }

      // Only handle arrow keys if we have results and not typing in an input
      if (
        !displayResult?.results.length ||
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      const results = displayResult.results;
      const currentIndex = selectedRowIndex ?? -1;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        const nextIndex = currentIndex < results.length - 1 ? currentIndex + 1 : currentIndex;
        setSelectedRowIndex(nextIndex);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : 0;
        setSelectedRowIndex(prevIndex);
      } else if (e.key === "Enter" && currentIndex >= 0) {
        e.preventDefault();
        const questionId = results[currentIndex].question_id;
        handleQuestionOpen(questionId);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [displayResult, selectedRowIndex, handleQuestionOpen]);

  // Display data (use previous if loading, current if available)
  const displayResult = loading && previousSearchResult ? previousSearchResult : searchResult;

  // Reset selected row when results change
  useEffect(() => {
    setSelectedRowIndex(null);
  }, [displayResult?.results.length]);

  // Handle filter changes
  const handleFilterChange = useCallback(
    (newFilters: SearchQueryParams) => {
      setFilters(newFilters);
      updateURL(newFilters);
    },
    [updateURL],
  );

  // Reset filters
  const handleResetFilters = useCallback(() => {
    const defaultFilters: SearchQueryParams = {
      page: 1,
      page_size: 25,
      sort: "relevance",
    };
    setFilters(defaultFilters);
    setSearchInput("");
    updateURL(defaultFilters);
  }, [updateURL]);

  // Handle query input change (local only, debounced)
  const handleQueryChange = useCallback((q: string) => {
    setSearchInput(q);
  }, []);

  // Handle sort change
  const handleSortChange = useCallback(
    (sort: "relevance" | "published_at_desc" | "updated_at_desc") => {
      handleFilterChange({ ...filters, sort, page: 1 });
    },
    [filters, handleFilterChange],
  );

  // Handle include unpublished toggle
  const handleIncludeUnpublishedChange = useCallback(
    (include: boolean) => {
      handleFilterChange({ ...filters, include_unpublished: include, page: 1 });
    },
    [filters, handleFilterChange],
  );

  // Handle pagination
  const handlePageChange = useCallback(
    (newPage: number) => {
      handleFilterChange({ ...filters, page: newPage });
    },
    [filters, handleFilterChange],
  );

  const handlePageSizeChange = useCallback(
    (newPageSize: number) => {
      handleFilterChange({ ...filters, page_size: newPageSize, page: 1 });
    },
    [filters, handleFilterChange],
  );

  // Check if user can include unpublished
  const canIncludeUnpublished = useMemo(() => {
    return user?.role === "ADMIN" || user?.role === "REVIEWER";
  }, [user]);

  // Handle question open (save to sessionStorage)
  const handleQuestionOpen = useCallback(
    (questionId: string) => {
      saveLastOpenedQuestion(searchParams, questionId);
      router.push(`/admin/questions/${questionId}`);
    },
    [router, searchParams],
  );

  // Handle row selection
  const handleRowSelect = useCallback((index: number) => {
    setSelectedRowIndex(index);
  }, []);

  // Calculate pagination info
  const totalPages = useMemo(() => {
    if (!displayResult) return 0;
    return Math.ceil(displayResult.total / (filters.page_size || 25));
  }, [displayResult, filters.page_size]);

  return (
    <div ref={containerRef} className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Questions</h1>
          <p className="text-muted-foreground">Manage and review all questions</p>
        </div>
        <Button onClick={() => router.push("/admin/questions/new")}>
          <Plus className="mr-2 h-4 w-4" />
          Create Question
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <SearchFiltersPanel
            filters={filters}
            onChange={handleFilterChange}
            onReset={handleResetFilters}
            searchResult={searchResult}
            userRole={user?.role || "STUDENT"}
          />
        </div>

        {/* Search + Results */}
        <div className="lg:col-span-3 space-y-4">
          {/* Search Bar Row */}
          <SearchBarRow
            q={searchInput}
            onQueryChange={handleQueryChange}
            sort={filters.sort || "relevance"}
            onSortChange={handleSortChange}
            includeUnpublished={filters.include_unpublished || false}
            onIncludeUnpublishedChange={handleIncludeUnpublishedChange}
            searchResult={searchResult}
            canIncludeUnpublished={canIncludeUnpublished}
          />

          {/* Results Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Questions</CardTitle>
                  <CardDescription>
                    {!loading && !error && displayResult
                      ? `${displayResult.total} question${displayResult.total !== 1 ? "s" : ""} found`
                      : loading && previousSearchResult
                        ? `${previousSearchResult.total} question${previousSearchResult.total !== 1 ? "s" : ""} found (updating...)`
                        : "Searching..."}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading && !previousSearchResult ? (
                <SkeletonTable rows={10} cols={8} />
              ) : error ? (
                <ErrorState
                  variant="card"
                  title="Failed to search questions"
                  description={error.message || "An error occurred while searching questions."}
                  actionLabel="Retry"
                  onAction={loadSearch}
                />
              ) : displayResult && displayResult.results.length === 0 ? (
                <EmptyState
                  variant="card"
                  title="No questions found"
                  description="No questions match your current filters. Try adjusting the filters or create a new question."
                  icon={<FileQuestion className="h-8 w-8 text-slate-400" />}
                  actionLabel={
                    filters.q || filters.status?.length || filters.cognitive_level?.length
                      ? "Reset Filters"
                      : "Create Question"
                  }
                  onAction={
                    filters.q || filters.status?.length || filters.cognitive_level?.length
                      ? handleResetFilters
                      : () => router.push("/admin/questions/new")
                  }
                />
              ) : displayResult ? (
                <div className="relative">
                  {loading && previousSearchResult && (
                    <div className="absolute inset-0 bg-background/30 backdrop-blur-[1px] z-10 flex items-center justify-center rounded-md">
                      <div className="text-xs text-muted-foreground bg-background px-2 py-1 rounded border">
                        Updating...
                      </div>
                    </div>
                  )}
                  <SearchResultsTable
                    results={displayResult.results}
                    selectedRowIndex={selectedRowIndex}
                    onRowSelect={handleRowSelect}
                    highlightedQuestionId={highlightedQuestionId}
                    onQuestionOpen={handleQuestionOpen}
                  />
                </div>
              ) : null}
            </CardContent>
          </Card>

          {/* Pagination */}
          {!loading && !error && displayResult && displayResult.results.length > 0 && (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Label htmlFor="page-size" className="text-sm">
                    Page size:
                  </Label>
                  <Select
                    value={(filters.page_size || 25).toString()}
                    onValueChange={(v) => handlePageSizeChange(parseInt(v))}
                  >
                    <SelectTrigger id="page-size" className="w-[80px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="25">25</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <p className="text-sm text-muted-foreground">
                  Page {filters.page || 1} of {totalPages} • {displayResult.total} total
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange((filters.page || 1) - 1)}
                  disabled={(filters.page || 1) <= 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange((filters.page || 1) + 1)}
                  disabled={(filters.page || 1) >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
