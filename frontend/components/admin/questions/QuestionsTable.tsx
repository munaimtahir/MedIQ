"use client";

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
import type { QuestionListItem, QuestionStatus } from "@/lib/types/question-cms";
import { FileEdit } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface QuestionsTableProps {
  questions: QuestionListItem[];
}

const STATUS_COLORS: Record<QuestionStatus, string> = {
  DRAFT: "bg-gray-500",
  IN_REVIEW: "bg-yellow-500",
  APPROVED: "bg-blue-500",
  PUBLISHED: "bg-green-500",
};

const STATUS_LABELS: Record<QuestionStatus, string> = {
  DRAFT: "Draft",
  IN_REVIEW: "In Review",
  APPROVED: "Approved",
  PUBLISHED: "Published",
};

export function QuestionsTable({ questions }: QuestionsTableProps) {
  const router = useRouter();

  const truncateText = (text: string | null, maxLength = 100) => {
    if (!text) return "—";
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
    } catch {
      return dateStr;
    }
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[100px]">Status</TableHead>
          <TableHead className="min-w-[300px]">Stem</TableHead>
          <TableHead>Tags</TableHead>
          <TableHead className="w-[120px]">Cognitive</TableHead>
          <TableHead className="w-[100px]">Difficulty</TableHead>
          <TableHead className="w-[150px]">Source</TableHead>
          <TableHead className="w-[150px]">Updated</TableHead>
          <TableHead className="w-[100px] text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {questions.length === 0 ? (
          <TableRow>
            <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
              No questions found
            </TableCell>
          </TableRow>
        ) : (
          questions.map((q) => (
            <TableRow key={q.id} className="hover:bg-muted/50">
              <TableCell>
                <Badge className={STATUS_COLORS[q.status]} variant="default">
                  {STATUS_LABELS[q.status]}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="max-w-md">
                  <p className="line-clamp-2 text-sm">{truncateText(q.stem, 150)}</p>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1">
                  {q.year_id && (
                    <span className="text-xs text-muted-foreground">Year {q.year_id}</span>
                  )}
                  {q.block_id && (
                    <span className="text-xs text-muted-foreground">Block {q.block_id}</span>
                  )}
                  {q.theme_id && (
                    <span className="text-xs text-muted-foreground">Theme {q.theme_id}</span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                {q.cognitive_level ? (
                  <Badge variant="outline" className="text-xs">
                    {q.cognitive_level}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {q.difficulty ? (
                  <Badge variant="secondary" className="text-xs">
                    {q.difficulty}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {q.source_book || q.source_page ? (
                  <div className="text-xs">
                    {q.source_book && <div className="truncate">{q.source_book}</div>}
                    {q.source_page && <div className="text-muted-foreground">{q.source_page}</div>}
                  </div>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                <span className="text-xs text-muted-foreground">{formatDate(q.updated_at)}</span>
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push(`/admin/questions/${q.id}`)}
                >
                  <FileEdit className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
