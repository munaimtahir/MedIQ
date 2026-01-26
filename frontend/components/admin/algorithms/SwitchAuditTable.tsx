"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ChevronDown, ChevronRight } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";
import type { SwitchEvent } from "@/lib/admin/algorithms/api";

interface SwitchAuditTableProps {
  events: SwitchEvent[];
  loading: boolean;
}

export function SwitchAuditTable({ events, loading }: SwitchAuditTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Switch Audit Trail</CardTitle>
          <CardDescription>Last 20 algorithm profile switches</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Switch Audit Trail</CardTitle>
        <CardDescription>Last 20 algorithm profile switches</CardDescription>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">No switch events recorded</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12"></TableHead>
                <TableHead>Time</TableHead>
                <TableHead>User</TableHead>
                <TableHead>From → To</TableHead>
                <TableHead>Overrides</TableHead>
                <TableHead>Freeze</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => {
                const isExpanded = expandedId === event.id;
                const overrides = event.new_config.config_json.overrides || {};
                const hasOverrides = Object.keys(overrides).length > 0;
                const isFrozen = event.new_config.config_json.safe_mode.freeze_updates;

                return (
                  <>
                    <TableRow
                      key={event.id}
                      className="cursor-pointer"
                      onClick={() => setExpandedId(isExpanded ? null : event.id)}
                    >
                      <TableCell>
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
                      </TableCell>
                      <TableCell className="text-sm font-mono text-xs">
                        {event.created_by.substring(0, 8)}...
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {event.previous_config.active_profile} → {event.new_config.active_profile}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {hasOverrides ? (
                          <Badge variant="secondary">
                            {Object.keys(overrides).length} override(s)
                          </Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">None</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {isFrozen ? (
                          <Badge variant="destructive">Frozen</Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-sm">
                        {event.reason || "-"}
                      </TableCell>
                    </TableRow>
                    {isExpanded && (
                      <TableRow>
                        <TableCell colSpan={7} className="bg-muted/50">
                          <div className="space-y-4 p-4">
                            <div>
                              <p className="text-sm font-semibold mb-2">Previous Configuration</p>
                              <pre className="text-xs bg-background p-3 rounded border overflow-x-auto">
                                {JSON.stringify(event.previous_config, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <p className="text-sm font-semibold mb-2">New Configuration</p>
                              <pre className="text-xs bg-background p-3 rounded border overflow-x-auto">
                                {JSON.stringify(event.new_config, null, 2)}
                              </pre>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
