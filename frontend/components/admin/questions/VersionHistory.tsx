"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { VersionOut, ChangeKind } from "@/lib/types/question-cms";
import { adminQuestionsApi } from "@/lib/admin/questionsApi";
import { formatDistanceToNow } from "@/lib/dateUtils";
import { History } from "lucide-react";

interface VersionHistoryProps {
  questionId: string;
}

const CHANGE_KIND_COLORS: Record<ChangeKind, string> = {
  CREATE: "bg-green-500",
  EDIT: "bg-blue-500",
  STATUS_CHANGE: "bg-yellow-500",
  PUBLISH: "bg-purple-500",
  UNPUBLISH: "bg-orange-500",
  IMPORT: "bg-gray-500",
};

const CHANGE_KIND_LABELS: Record<ChangeKind, string> = {
  CREATE: "Created",
  EDIT: "Edited",
  STATUS_CHANGE: "Status Changed",
  PUBLISH: "Published",
  UNPUBLISH: "Unpublished",
  IMPORT: "Imported",
};

export function VersionHistory({ questionId }: VersionHistoryProps) {
  const [versions, setVersions] = useState<VersionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadVersions();
  }, [questionId]);

  const loadVersions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminQuestionsApi.listVersions(questionId);
      setVersions(data);
    } catch (err) {
      console.error("Failed to load version history:", err);
      setError(err instanceof Error ? err.message : "Failed to load version history");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
    } catch {
      return dateStr;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <History className="h-5 w-5" />
          <CardTitle>Version History</CardTitle>
        </div>
        <CardDescription>Track all changes to this question</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading version history...</p>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : versions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No version history available</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[80px]">Version</TableHead>
                <TableHead>Change Type</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead className="w-[150px]">When</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {versions.map((version) => (
                <TableRow key={version.id}>
                  <TableCell className="font-medium">v{version.version_no}</TableCell>
                  <TableCell>
                    <Badge className={CHANGE_KIND_COLORS[version.change_kind]}>
                      {CHANGE_KIND_LABELS[version.change_kind]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {version.change_reason || "—"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(version.changed_at)}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
