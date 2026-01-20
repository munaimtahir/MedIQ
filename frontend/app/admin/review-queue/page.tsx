"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { adminQuestionsApi } from "@/lib/admin/questionsApi";
import type { QuestionListItem } from "@/lib/types/question-cms";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { CheckSquare, Search, AlertCircle, CheckCircle, FileText } from "lucide-react";
import { useDebounce } from "@/lib/hooks/useDebounce";

export default function ReviewQueuePage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<QuestionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounce(searchInput, 500);

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminQuestionsApi.listQuestions({
        status: "IN_REVIEW",
        q: debouncedSearch || undefined,
        page: 1,
        page_size: 50,
        sort: "updated_at",
        order: "desc",
      });
      setQuestions(data);
    } catch (err) {
      console.error("Failed to load review queue:", err);
      setError(err instanceof Error ? err : new Error("Failed to load review queue"));
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const truncateText = (text: string | null, maxLength = 150) => {
    if (!text) return "—";
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  const getCompletenessIndicator = (question: QuestionListItem) => {
    const hasAllOptions = true; // We can't check this from list view
    const hasTags = question.year_id && question.block_id && question.theme_id;
    const hasSource = question.source_book && question.source_page;
    const hasCognitive = question.cognitive_level;
    const hasDifficulty = question.difficulty;

    const completeness = [hasTags, hasSource, hasCognitive, hasDifficulty].filter(Boolean).length;
    const total = 4;

    return {
      score: completeness,
      total,
      percentage: (completeness / total) * 100,
    };
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <CheckSquare className="h-8 w-8" />
            <h1 className="text-3xl font-bold">Review Queue</h1>
          </div>
          <p className="text-muted-foreground">Questions awaiting review and approval</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-lg px-4 py-2">
            {questions.length} in queue
          </Badge>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Pending Reviews</CardTitle>
              <CardDescription>Questions with IN_REVIEW status</CardDescription>
            </div>
            <div className="w-64">
              <Label htmlFor="search" className="sr-only">
                Search
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search questions..."
                  className="pl-9"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <SkeletonTable rows={8} cols={6} />
          ) : error ? (
            <ErrorState
              variant="card"
              title="Failed to load review queue"
              description={error.message || "An error occurred while loading the review queue."}
              actionLabel="Retry"
              onAction={loadQuestions}
            />
          ) : questions.length === 0 ? (
            <EmptyState
              variant="card"
              title="No questions in review"
              description={
                debouncedSearch
                  ? "No questions match your search"
                  : "All caught up! There are no questions pending review."
              }
              icon={<CheckSquare className="h-8 w-8 text-slate-400" />}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[400px]">Stem</TableHead>
                  <TableHead className="w-[120px]">Tags</TableHead>
                  <TableHead className="w-[120px]">Metadata</TableHead>
                  <TableHead className="w-[100px]">Source</TableHead>
                  <TableHead className="w-[120px]">Completeness</TableHead>
                  <TableHead className="w-[150px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {questions.map((q) => {
                  const completeness = getCompletenessIndicator(q);
                  return (
                    <TableRow key={q.id} className="hover:bg-muted/50">
                      <TableCell>
                        <div className="max-w-md">
                          <p className="text-sm line-clamp-2">{truncateText(q.stem, 200)}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        {q.year_id && q.block_id && q.theme_id ? (
                          <div className="flex items-center gap-1">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-xs text-muted-foreground">Complete</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1">
                            <AlertCircle className="h-4 w-4 text-yellow-500" />
                            <span className="text-xs text-muted-foreground">Incomplete</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        {q.cognitive_level && q.difficulty ? (
                          <div className="flex items-center gap-1">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-xs text-muted-foreground">Complete</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1">
                            <AlertCircle className="h-4 w-4 text-yellow-500" />
                            <span className="text-xs text-muted-foreground">Incomplete</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        {q.source_book ? (
                          <div className="flex items-center gap-1">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          </div>
                        ) : (
                          <div className="flex items-center gap-1">
                            <AlertCircle className="h-4 w-4 text-yellow-500" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-muted rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full ${completeness.percentage >= 75 ? "bg-green-500" : completeness.percentage >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                              style={{ width: `${completeness.percentage}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {completeness.score}/{completeness.total}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => router.push(`/admin/questions/${q.id}?mode=review`)}
                        >
                          <FileText className="mr-2 h-4 w-4" />
                          Review
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-base">Review Guidelines</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <ul className="list-disc list-inside space-y-1 text-muted-foreground">
            <li>Check that the question stem is clear and unambiguous</li>
            <li>Verify all 5 options are present and the correct answer is marked</li>
            <li>Ensure the explanation is comprehensive and helpful</li>
            <li>Confirm all required tagging (Year, Block, Theme) is complete</li>
            <li>Check cognitive level and difficulty are appropriate</li>
            <li>Verify source attribution when provided</li>
            <li>Approve if all criteria are met, or reject with specific feedback</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
