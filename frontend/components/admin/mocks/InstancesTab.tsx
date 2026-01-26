"use client";

import { useState, useEffect, useCallback } from "react";
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
import { Eye, Download } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { adminMocksAPI, type MockInstance } from "@/lib/api/adminMocks";
import { notify } from "@/lib/notify";
import { formatDistanceToNow } from "date-fns";

export function InstancesTab() {
  const [instances, setInstances] = useState<MockInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewingInstance, setViewingInstance] = useState<MockInstance | null>(null);

  const fetchInstances = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminMocksAPI.listInstances({ limit: 50 });
      setInstances(data);
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to load instances", err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInstances();
  }, [fetchInstances]);

  const handleViewInstance = async (instanceId: string) => {
    try {
      const instance = await adminMocksAPI.getInstance(instanceId);
      setViewingInstance(instance);
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to load instance", err.message);
    }
  };

  const handleExportJSON = (instance: MockInstance) => {
    const exportData = {
      instance_id: instance.id,
      blueprint_id: instance.blueprint_id,
      year: instance.year,
      total_questions: instance.total_questions,
      duration_minutes: instance.duration_minutes,
      seed: instance.seed,
      question_ids: instance.question_ids,
      meta: instance.meta,
      created_at: instance.created_at,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mock-instance-${instance.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <div className="text-muted-foreground">Loading instances...</div>;
  }

  return (
    <div className="space-y-4">
      {instances.length === 0 ? (
        <div className="rounded-lg border p-8 text-center text-muted-foreground">
          No instances found. Generate a mock to create an instance.
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Created</TableHead>
                <TableHead>Blueprint ID</TableHead>
                <TableHead>Questions</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Seed</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {instances.map((instance) => (
                <TableRow key={instance.id}>
                  <TableCell>
                    {formatDistanceToNow(new Date(instance.created_at), { addSuffix: true })}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{instance.blueprint_id}</TableCell>
                  <TableCell>{instance.total_questions}</TableCell>
                  <TableCell>{instance.duration_minutes} min</TableCell>
                  <TableCell className="font-mono text-xs">{instance.seed}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewInstance(instance.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleExportJSON(instance)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Instance Detail Dialog */}
      {viewingInstance && (
        <Dialog open={!!viewingInstance} onOpenChange={() => setViewingInstance(null)}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Mock Instance Details</DialogTitle>
              <DialogDescription>
                Question set generated from blueprint
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground">Instance ID</div>
                  <div className="font-mono text-sm">{viewingInstance.id}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Blueprint ID</div>
                  <div className="font-mono text-sm">{viewingInstance.blueprint_id}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Total Questions</div>
                  <div>{viewingInstance.total_questions}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Duration</div>
                  <div>{viewingInstance.duration_minutes} minutes</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Seed</div>
                  <div className="font-mono text-sm">{viewingInstance.seed}</div>
                </div>
              </div>

              {viewingInstance.meta && (
                <div>
                  <div className="font-semibold mb-2">Metadata</div>
                  <pre className="text-xs bg-muted p-3 rounded border overflow-auto max-h-48">
                    {JSON.stringify(viewingInstance.meta, null, 2)}
                  </pre>
                </div>
              )}

              <div>
                <div className="font-semibold mb-2">Question IDs ({viewingInstance.question_ids.length})</div>
                <div className="max-h-96 overflow-auto rounded border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>#</TableHead>
                        <TableHead>Question ID</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {viewingInstance.question_ids.map((qid, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{idx + 1}</TableCell>
                          <TableCell className="font-mono text-xs">{qid}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
