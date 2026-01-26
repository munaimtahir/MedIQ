"use client";

import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";
import type { RuntimeStatus } from "@/lib/api/adminLearningOps";

interface AuditTrailTabsProps {
  runtime: RuntimeStatus | null;
  loading?: boolean;
}

export function AuditTrailTabs({ runtime, loading }: AuditTrailTabsProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const switchEvents = runtime?.last_switch_events || [];

  return (
    <Tabs defaultValue="runtime" className="w-full">
      <TabsList>
        <TabsTrigger value="runtime">Runtime Switches</TabsTrigger>
        <TabsTrigger value="irt">IRT Events</TabsTrigger>
        <TabsTrigger value="rank">Rank Events</TabsTrigger>
        <TabsTrigger value="graph">Graph Events</TabsTrigger>
        <TabsTrigger value="blocked">Blocked/Failures</TabsTrigger>
      </TabsList>

      <TabsContent value="runtime" className="space-y-4">
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Profile</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>By</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : switchEvents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    No switch events
                  </TableCell>
                </TableRow>
              ) : (
                switchEvents.map((event) => {
                  const isExpanded = expandedRows.has(event.id);
                  return (
                    <React.Fragment key={event.id}>
                      <TableRow>
                        <TableCell className="text-sm">
                          {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {(event.new_config as { active_profile?: string })?.active_profile || "N/A"}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-md truncate">{event.reason || "—"}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{event.created_by}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleRow(event.id)}
                          >
                            {isExpanded ? (
                              <ChevronUp className="h-4 w-4" />
                            ) : (
                              <ChevronDown className="h-4 w-4" />
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                      {isExpanded && (
                        <TableRow>
                          <TableCell colSpan={5} className="bg-muted/50">
                            <div className="p-4 space-y-2">
                              <div>
                                <strong className="text-sm">Previous Config:</strong>
                                <pre className="mt-1 text-xs bg-background p-2 rounded overflow-auto max-h-32">
                                  {JSON.stringify(event.previous_config, null, 2)}
                                </pre>
                              </div>
                              <div>
                                <strong className="text-sm">New Config:</strong>
                                <pre className="mt-1 text-xs bg-background p-2 rounded overflow-auto max-h-32">
                                  {JSON.stringify(event.new_config, null, 2)}
                                </pre>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </TabsContent>

      <TabsContent value="irt" className="space-y-4">
        <div className="rounded-md border p-4 text-center text-muted-foreground">
          IRT activation events will appear here. TODO: Implement IRT events endpoint.
        </div>
      </TabsContent>

      <TabsContent value="rank" className="space-y-4">
        <div className="rounded-md border p-4 text-center text-muted-foreground">
          Rank activation events will appear here. TODO: Implement Rank events endpoint.
        </div>
      </TabsContent>

      <TabsContent value="graph" className="space-y-4">
        <div className="rounded-md border p-4 text-center text-muted-foreground">
          Graph revision activation events will appear here. TODO: Implement Graph events endpoint.
        </div>
      </TabsContent>

      <TabsContent value="blocked" className="space-y-4">
        <div className="rounded-md border p-4 text-center text-muted-foreground">
          Blocked/failed runs will appear here. TODO: Implement blocked runs endpoint.
        </div>
      </TabsContent>
    </Tabs>
  );
}
