"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight } from "lucide-react";
import { adminMocksAPI, type MockGenerationRun } from "@/lib/api/adminMocks";
import { notify } from "@/lib/notify";
import { formatDistanceToNow } from "date-fns";

export function RunsTab() {
  const [runs, setRuns] = useState<MockGenerationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminMocksAPI.listRuns({ limit: 50 });
      setRuns(data);
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to load runs", err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const toggleRow = (runId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(runId)) {
      newExpanded.delete(runId);
    } else {
      newExpanded.add(runId);
    }
    setExpandedRows(newExpanded);
  };

  if (loading) {
    return <div className="text-muted-foreground">Loading runs...</div>;
  }

  return (
    <div className="space-y-4">
      {runs.length === 0 ? (
        <div className="rounded-lg border p-8 text-center text-muted-foreground">
          No generation runs found.
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12"></TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Blueprint ID</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Seed</TableHead>
                <TableHead>Questions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => {
                const isExpanded = expandedRows.has(run.id);
                return (
                  <Fragment key={run.id}>
                    <TableRow>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleRow(run.id)}
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </Button>
                      </TableCell>
                      <TableCell>
                        {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{run.blueprint_id}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            run.status === "done"
                              ? "default"
                              : run.status === "failed"
                                ? "destructive"
                                : "secondary"
                          }
                        >
                          {run.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{run.seed}</TableCell>
                      <TableCell>{run.generated_question_count}</TableCell>
                    </TableRow>
                    {isExpanded && (
                      <TableRow>
                        <TableCell colSpan={6} className="bg-muted/50">
                          <div className="space-y-4 p-4">
                            {run.warnings && run.warnings.length > 0 && (
                              <div>
                                <div className="font-semibold mb-2">Warnings</div>
                                <pre className="text-xs bg-background p-3 rounded border overflow-auto max-h-48">
                                  {JSON.stringify(run.warnings, null, 2)}
                                </pre>
                              </div>
                            )}
                            {run.errors && run.errors.length > 0 && (
                              <div>
                                <div className="font-semibold mb-2 text-destructive">Errors</div>
                                <pre className="text-xs bg-background p-3 rounded border overflow-auto max-h-48">
                                  {JSON.stringify(run.errors, null, 2)}
                                </pre>
                              </div>
                            )}
                            {run.finished_at && (
                              <div className="text-sm text-muted-foreground">
                                Finished: {new Date(run.finished_at).toLocaleString()}
                              </div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
