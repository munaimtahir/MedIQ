"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { QuestionFilters } from "@/components/admin/questions/QuestionFilters";
import { QuestionsTable } from "@/components/admin/questions/QuestionsTable";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { adminQuestionsApi } from "@/lib/admin/questionsApi";
import type { QuestionListItem, QuestionListQuery } from "@/lib/types/question-cms";
import { FileQuestion, Plus } from "lucide-react";

export default function QuestionsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [questions, setQuestions] = useState<QuestionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Parse filters from URL
  const getFiltersFromURL = useCallback((): QuestionListQuery => {
    const params: QuestionListQuery = {
      page: 1,
      page_size: 20,
      sort: "updated_at",
      order: "desc",
    };

    const status = searchParams.get("status");
    const year_id = searchParams.get("year_id");
    const block_id = searchParams.get("block_id");
    const theme_id = searchParams.get("theme_id");
    const difficulty = searchParams.get("difficulty");
    const cognitive_level = searchParams.get("cognitive_level");
    const q = searchParams.get("q");
    const page = searchParams.get("page");
    const page_size = searchParams.get("page_size");

    if (status) params.status = status as QuestionListQuery["status"];
    if (year_id) params.year_id = Number(year_id);
    if (block_id) params.block_id = Number(block_id);
    if (theme_id) params.theme_id = Number(theme_id);
    if (difficulty) params.difficulty = difficulty;
    if (cognitive_level) params.cognitive_level = cognitive_level;
    if (q) params.q = q;
    if (page) params.page = Number(page);
    if (page_size) params.page_size = Number(page_size);

    return params;
  }, [searchParams]);

  const [filters, setFilters] = useState<QuestionListQuery>(getFiltersFromURL());

  // Update URL when filters change
  const updateURL = useCallback(
    (newFilters: QuestionListQuery) => {
      const params = new URLSearchParams();

      if (newFilters.status) params.set("status", newFilters.status);
      if (newFilters.year_id) params.set("year_id", newFilters.year_id.toString());
      if (newFilters.block_id) params.set("block_id", newFilters.block_id.toString());
      if (newFilters.theme_id) params.set("theme_id", newFilters.theme_id.toString());
      if (newFilters.difficulty) params.set("difficulty", newFilters.difficulty);
      if (newFilters.cognitive_level) params.set("cognitive_level", newFilters.cognitive_level);
      if (newFilters.q) params.set("q", newFilters.q);
      if (newFilters.page && newFilters.page > 1) params.set("page", newFilters.page.toString());
      if (newFilters.page_size && newFilters.page_size !== 20)
        params.set("page_size", newFilters.page_size.toString());

      const queryString = params.toString();
      router.push(`/admin/questions${queryString ? `?${queryString}` : ""}`, { scroll: false });
    },
    [router],
  );

  // Load questions
  const loadQuestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminQuestionsApi.listQuestions(filters);
      setQuestions(data);
    } catch (err) {
      console.error("Failed to load questions:", err);
      setError(err instanceof Error ? err : new Error("Failed to load questions"));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Load questions when filters change
  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  // Handle filter changes
  const handleFilterChange = (newFilters: QuestionListQuery) => {
    setFilters(newFilters);
    updateURL(newFilters);
  };

  // Reset filters
  const handleResetFilters = () => {
    const defaultFilters: QuestionListQuery = {
      page: 1,
      page_size: 20,
      sort: "updated_at",
      order: "desc",
    };
    setFilters(defaultFilters);
    updateURL(defaultFilters);
  };

  return (
    <div className="space-y-6">
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
          <QuestionFilters
            filters={filters}
            onChange={handleFilterChange}
            onReset={handleResetFilters}
          />
        </div>

        {/* Questions List */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>Questions</CardTitle>
              <CardDescription>
                {!loading && !error && `${questions.length} questions found`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <SkeletonTable rows={10} cols={8} />
              ) : error ? (
                <ErrorState
                  variant="card"
                  title="Failed to load questions"
                  description={error.message || "An error occurred while loading questions."}
                  actionLabel="Retry"
                  onAction={loadQuestions}
                />
              ) : questions.length === 0 ? (
                <EmptyState
                  variant="card"
                  title="No questions found"
                  description="No questions match your current filters. Try adjusting the filters or create a new question."
                  icon={<FileQuestion className="h-8 w-8 text-slate-400" />}
                  actionLabel={filters.q || filters.status ? "Reset Filters" : "Create Question"}
                  onAction={
                    filters.q || filters.status
                      ? handleResetFilters
                      : () => router.push("/admin/questions/new")
                  }
                />
              ) : (
                <QuestionsTable questions={questions} />
              )}
            </CardContent>
          </Card>

          {/* Pagination - Simple version for now */}
          {!loading && !error && questions.length > 0 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {filters.page || 1} • {questions.length} items
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleFilterChange({ ...filters, page: (filters.page || 1) - 1 })}
                  disabled={(filters.page || 1) <= 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleFilterChange({ ...filters, page: (filters.page || 1) + 1 })}
                  disabled={questions.length < (filters.page_size || 20)}
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
