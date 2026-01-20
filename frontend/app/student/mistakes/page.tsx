"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { AlertTriangle, Info, TrendingDown, Target, ChevronRight } from "lucide-react";
import { notify } from "@/lib/notify";
import {
  getMistakesSummary,
  getMistakesList,
  type MistakesSummaryResponse,
  type MistakeItem,
} from "@/lib/api/mistakesApi";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { format } from "date-fns";

const MISTAKE_TYPE_LABELS: Record<string, string> = {
  FAST_WRONG: "Fast Wrong",
  SLOW_WRONG: "Slow Wrong",
  CHANGED_ANSWER_WRONG: "Changed Answer",
  TIME_PRESSURE_WRONG: "Time Pressure",
  DISTRACTED_WRONG: "Distracted",
  KNOWLEDGE_GAP: "Knowledge Gap",
};

const MISTAKE_TYPE_COLORS: Record<string, "destructive" | "default" | "secondary" | "outline"> = {
  FAST_WRONG: "destructive",
  SLOW_WRONG: "default",
  CHANGED_ANSWER_WRONG: "secondary",
  TIME_PRESSURE_WRONG: "default",
  DISTRACTED_WRONG: "secondary",
  KNOWLEDGE_GAP: "outline",
};

function getSeverityIndicator(severity: number) {
  const dots = Array(severity).fill("●");
  const color = severity >= 2 ? "text-red-600" : "text-yellow-600";
  return <span className={color}>{dots.join("")}</span>;
}

interface MistakeCardProps {
  mistake: MistakeItem;
  onPracticeTheme: (themeId: string, themeName: string) => void;
}

function MistakeCard({ mistake, onPracticeTheme }: MistakeCardProps) {
  const mistakeLabel = MISTAKE_TYPE_LABELS[mistake.mistake_type] || mistake.mistake_type;
  const mistakeColor = MISTAKE_TYPE_COLORS[mistake.mistake_type] || "outline";

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <Badge variant={mistakeColor}>{mistakeLabel}</Badge>
              <Badge variant="outline">{mistake.block.name}</Badge>
              <Badge variant="secondary">{mistake.theme.name}</Badge>
              <span className="text-sm font-medium">{getSeverityIndicator(mistake.severity)}</span>
            </div>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <p className="text-sm text-muted-foreground line-clamp-2">
                {mistake.question.stem_preview}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Info className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80">
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm">Evidence</h4>
                  <div className="space-y-2 text-sm">
                    {mistake.evidence.time_spent_sec !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Time spent:</span>
                        <span className="font-medium">{mistake.evidence.time_spent_sec}s</span>
                      </div>
                    )}
                    {mistake.evidence.change_count !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Changes made:</span>
                        <span className="font-medium">{mistake.evidence.change_count}</span>
                      </div>
                    )}
                    {mistake.evidence.blur_count !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Blur events:</span>
                        <span className="font-medium">{mistake.evidence.blur_count}</span>
                      </div>
                    )}
                    {mistake.evidence.remaining_sec_at_answer !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Time remaining:</span>
                        <span className="font-medium">{mistake.evidence.remaining_sec_at_answer}s</span>
                      </div>
                    )}
                    {mistake.evidence.mark_for_review_used !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Marked for review:</span>
                        <span className="font-medium">
                          {mistake.evidence.mark_for_review_used ? "Yes" : "No"}
                        </span>
                      </div>
                    )}
                    {mistake.evidence.rule_fired && (
                      <div className="pt-2 border-t">
                        <span className="text-xs text-muted-foreground">
                          Rule: {mistake.evidence.rule_fired}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{format(new Date(mistake.created_at), "MMM d, yyyy 'at' h:mm a")}</span>
          <Button
            variant="link"
            size="sm"
            className="h-auto p-0"
            onClick={() => onPracticeTheme(mistake.theme.id, mistake.theme.name)}
          >
            Practice this theme
            <ChevronRight className="ml-1 h-3 w-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function MistakesPage() {
  const router = useRouter();
  const [rangeDays, setRangeDays] = useState<number>(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<MistakesSummaryResponse | null>(null);
  const [mistakes, setMistakes] = useState<MistakeItem[]>([]);
  const [selectedBlock, setSelectedBlock] = useState<string>("");
  const [selectedMistakeType, setSelectedMistakeType] = useState<string>("");
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    loadData();
  }, [rangeDays, selectedBlock, selectedMistakeType]);

  async function loadData() {
    setLoading(true);
    setError(null);
    setPage(1);

    try {
      const [summaryData, mistakesData] = await Promise.all([
        getMistakesSummary(rangeDays),
        getMistakesList({
          rangeDays,
          blockId: selectedBlock || undefined,
          mistakeType: selectedMistakeType || undefined,
          page: 1,
          pageSize: 20,
        }),
      ]);

      setSummary(summaryData);
      setMistakes(mistakesData.items);
      setHasMore(mistakesData.items.length < mistakesData.total);
    } catch (err: any) {
      console.error("Failed to load mistakes:", err);
      setError(err?.message || "Failed to load mistakes");
    } finally {
      setLoading(false);
    }
  }

  async function loadMore() {
    if (loadingMore || !hasMore) return;

    setLoadingMore(true);
    const nextPage = page + 1;

    try {
      const mistakesData = await getMistakesList({
        rangeDays,
        blockId: selectedBlock || undefined,
        mistakeType: selectedMistakeType || undefined,
        page: nextPage,
        pageSize: 20,
      });

      setMistakes((prev) => [...prev, ...mistakesData.items]);
      setPage(nextPage);
      setHasMore(prev.length + mistakesData.items.length < mistakesData.total);
    } catch (err: any) {
      console.error("Failed to load more mistakes:", err);
      notify.error("Failed to load more", err?.message || "Please try again");
    } finally {
      setLoadingMore(false);
    }
  }

  function handlePracticeTheme(themeId: string, themeName: string) {
    const params = new URLSearchParams({
      themeId,
      count: "15",
    });
    router.push(`/student/practice/build?${params}`);
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-10 w-64 mb-2" />
          <Skeleton className="h-5 w-96" />
        </div>
        <Skeleton className="h-12 w-full" />
        <div className="grid gap-6 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">Mistakes</h1>
          <p className="text-muted-foreground">Learn from your errors</p>
        </div>
        <Card>
          <CardContent className="py-6">
            <InlineAlert variant="error" message={error} />
            <Button onClick={loadData} className="mt-4">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const uniqueBlocks = summary?.top_blocks.map((b) => ({ id: b.block.id, name: b.block.name })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <AlertTriangle className="h-8 w-8" />
          Mistakes
        </h1>
        <p className="text-muted-foreground">Learn from your errors and improve</p>
      </div>

      {/* Range Selector */}
      <div className="flex gap-2">
        <Button
          variant={rangeDays === 7 ? "default" : "outline"}
          size="sm"
          onClick={() => setRangeDays(7)}
        >
          Last 7 days
        </Button>
        <Button
          variant={rangeDays === 30 ? "default" : "outline"}
          size="sm"
          onClick={() => setRangeDays(30)}
        >
          Last 30 days
        </Button>
        <Button
          variant={rangeDays === 90 ? "default" : "outline"}
          size="sm"
          onClick={() => setRangeDays(90)}
        >
          Last 90 days
        </Button>
      </div>

      {/* Summary Cards */}
      {summary && summary.total_wrong > 0 && (
        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Total Wrong</CardDescription>
              <CardTitle className="text-3xl">{summary.total_wrong}</CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Most Common Type</CardDescription>
              <CardTitle className="text-lg">
                {Object.entries(summary.counts_by_type).length > 0 ? (
                  (() => {
                    const sorted = Object.entries(summary.counts_by_type).sort((a, b) => b[1] - a[1]);
                    return (
                      <div className="space-y-1">
                        <div className="text-2xl">{MISTAKE_TYPE_LABELS[sorted[0][0]] || sorted[0][0]}</div>
                        <div className="text-sm text-muted-foreground">({sorted[0][1]} times)</div>
                      </div>
                    );
                  })()
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Weakest Theme</CardDescription>
              <CardTitle className="text-lg">
                {summary.top_themes.length > 0 ? (
                  <div className="space-y-1">
                    <div className="text-base">{summary.top_themes[0].theme.name}</div>
                    <div className="text-sm text-muted-foreground">({summary.top_themes[0].wrong} wrong)</div>
                  </div>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* Filters */}
      {mistakes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 flex-wrap">
              <div className="w-full sm:w-64">
                <Select value={selectedBlock} onValueChange={setSelectedBlock}>
                  <SelectTrigger>
                    <SelectValue placeholder="All blocks" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All blocks</SelectItem>
                    {uniqueBlocks.map((block) => (
                      <SelectItem key={block.id} value={block.id}>
                        {block.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="w-full sm:w-64">
                <Select value={selectedMistakeType} onValueChange={setSelectedMistakeType}>
                  <SelectTrigger>
                    <SelectValue placeholder="All mistake types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All mistake types</SelectItem>
                    {Object.entries(MISTAKE_TYPE_LABELS).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {(selectedBlock || selectedMistakeType) && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setSelectedBlock("");
                    setSelectedMistakeType("");
                  }}
                >
                  Clear filters
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Mistakes List */}
      {mistakes.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center text-muted-foreground">
              <Target className="mx-auto mb-4 h-16 w-16 opacity-30" />
              <p className="text-lg font-medium mb-2">No mistakes in this range</p>
              <p className="text-sm">
                {summary && summary.total_wrong === 0
                  ? "You haven't made any mistakes yet. Keep up the great work!"
                  : "Try adjusting the time range or filters"}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Showing {mistakes.length} mistake{mistakes.length !== 1 ? "s" : ""}
            </p>
          </div>

          {mistakes.map((mistake) => (
            <MistakeCard
              key={`${mistake.created_at}-${mistake.question.id}`}
              mistake={mistake}
              onPracticeTheme={handlePracticeTheme}
            />
          ))}

          {hasMore && (
            <div className="flex justify-center pt-4">
              <Button onClick={loadMore} disabled={loadingMore} variant="outline">
                {loadingMore ? "Loading..." : "Load More"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
