"use client";

import { memo, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SearchResultItem } from "@/lib/types/search";
import { FileEdit } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";
import { adminQuestionsApi } from "@/lib/admin/questionsApi";
import { prefetchCache } from "@/lib/admin/questions/prefetchCache";
import { useDebounce } from "@/lib/hooks/useDebounce";

interface SearchResultsTableProps {
  results: SearchResultItem[];
  selectedRowIndex: number | null;
  onRowSelect: (index: number) => void;
  highlightedQuestionId: string | null;
  onQuestionOpen: (questionId: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-gray-500",
  IN_REVIEW: "bg-yellow-500",
  APPROVED: "bg-blue-500",
  PUBLISHED: "bg-green-500",
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Draft",
  IN_REVIEW: "In Review",
  APPROVED: "Approved",
  PUBLISHED: "Published",
};

// Helper functions outside component to prevent recreation
const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return "—";
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
  } catch {
    return dateStr;
  }
};

export const SearchResultsTable = memo(function SearchResultsTable({
  results,
  selectedRowIndex,
  onRowSelect,
  highlightedQuestionId,
  onQuestionOpen,
}: SearchResultsTableProps) {
  const router = useRouter();
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);

  // Prefetch on hover/focus with debounce
  const [hoveredQuestionId, setHoveredQuestionId] = useState<string | null>(null);
  const debouncedHoveredId = useDebounce(hoveredQuestionId, 120);

  useEffect(() => {
    if (debouncedHoveredId && prefetchCache.recordHover(debouncedHoveredId)) {
      // Check if already cached
      const cached = prefetchCache.get(debouncedHoveredId);
      if (cached) return;

      // Prefetch the question
      const promise = adminQuestionsApi.getQuestion(debouncedHoveredId).catch(() => {
        // Silently fail - prefetch is best effort
      });
      prefetchCache.set(debouncedHoveredId, promise);
    }
  }, [debouncedHoveredId]);

  const handleRowClick = useCallback(
    (questionId: string) => {
      onQuestionOpen(questionId);
      router.push(`/admin/questions/${questionId}`);
    },
    [router, onQuestionOpen],
  );

  const handleRowHover = useCallback((questionId: string) => {
    setHoveredQuestionId(questionId);
  }, []);

  const handleRowFocus = useCallback(
    (questionId: string, index: number) => {
      onRowSelect(index);
      setHoveredQuestionId(questionId);
    },
    [onRowSelect],
  );

  // Scroll selected row into view
  useEffect(() => {
    if (selectedRowIndex !== null && rowRefs.current[selectedRowIndex]) {
      rowRefs.current[selectedRowIndex]?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [selectedRowIndex]);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[100px]">Status</TableHead>
          <TableHead className="min-w-[300px]">Stem Preview</TableHead>
          <TableHead>Tags</TableHead>
          <TableHead className="w-[120px]">Cognitive</TableHead>
          <TableHead className="w-[100px]">Difficulty</TableHead>
          <TableHead className="w-[150px]">Source</TableHead>
          <TableHead className="w-[150px]">Updated</TableHead>
          <TableHead className="w-[100px] text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {results.length === 0 ? (
          <TableRow>
            <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
              No questions found
            </TableCell>
          </TableRow>
        ) : (
          results.map((result, index) => {
            const isSelected = selectedRowIndex === index;
            const isHighlighted = highlightedQuestionId === result.question_id;
            return (
              <TableRow
                key={`${result.question_id}:${result.version_id || ""}`}
                ref={(el) => {
                  rowRefs.current[index] = el;
                }}
                className={`hover:bg-muted/50 cursor-pointer ${
                  isSelected ? "bg-muted ring-2 ring-ring ring-offset-2" : ""
                } ${
                  isHighlighted && !isSelected
                    ? "bg-yellow-50 dark:bg-yellow-950/20 border-l-4 border-yellow-500"
                    : ""
                }`}
                onClick={() => handleRowClick(result.question_id)}
                onMouseEnter={() => handleRowHover(result.question_id)}
                onFocus={() => handleRowFocus(result.question_id, index)}
                tabIndex={0}
                role="row"
                aria-selected={isSelected}
              >
              <TableCell>
                <Badge
                  className={STATUS_COLORS[result.status] || "bg-gray-500"}
                  variant="default"
                >
                  {STATUS_LABELS[result.status] || result.status}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="max-w-md">
                  <p className="line-clamp-2 text-sm">{result.stem_preview || "—"}</p>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1">
                  {result.year && (
                    <span className="text-xs text-muted-foreground">Year {result.year}</span>
                  )}
                  {result.block_id && (
                    <span className="text-xs text-muted-foreground">Block {result.block_id}</span>
                  )}
                  {result.theme_id && (
                    <span className="text-xs text-muted-foreground">Theme {result.theme_id}</span>
                  )}
                  {result.tags_preview && (
                    <span className="text-xs text-muted-foreground truncate">
                      {result.tags_preview}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                {result.cognitive_level ? (
                  <Badge variant="outline" className="text-xs">
                    {result.cognitive_level}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {result.difficulty_label ? (
                  <Badge variant="secondary" className="text-xs">
                    {result.difficulty_label}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {result.source_book || result.source_page ? (
                  <div className="text-xs">
                    {result.source_book && <div className="truncate">{result.source_book}</div>}
                    {result.source_page && (
                      <div className="text-muted-foreground">p. {result.source_page}</div>
                    )}
                  </div>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                <span className="text-xs text-muted-foreground">
                  {formatDate(result.updated_at)}
                </span>
              </TableCell>
              <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRowClick(result.question_id)}
                >
                  <FileEdit className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
            );
          })
        )}
      </TableBody>
    </Table>
  );
});
