"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useBridgeStatus } from "@/lib/admin/algorithms/hooks";
import { formatDistanceToNow } from "@/lib/dateUtils";
import type { BridgeStatusPayload } from "@/lib/admin/algorithms/api";

interface HealthCardProps {
  bridgeSummary: {
    counts_by_status: Record<string, number>;
    total: number;
  } | null;
}

export function HealthCard({ bridgeSummary }: HealthCardProps) {
  const [userId, setUserId] = useState("");
  const [searchUserId, setSearchUserId] = useState<string | undefined>(undefined);
  const { data: bridgeData, loading: bridgeLoading, refetch: fetchBridgeStatus } = useBridgeStatus(searchUserId);

  const handleSearch = () => {
    if (userId.trim()) {
      setSearchUserId(userId.trim());
    }
  };

  // Trigger fetch when searchUserId changes
  useEffect(() => {
    if (searchUserId) {
      fetchBridgeStatus();
    }
  }, [searchUserId, fetchBridgeStatus]);

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "success"> = {
      done: "success",
      running: "default",
      queued: "secondary",
      failed: "destructive",
    };
    return <Badge variant={variants[status] || "secondary"}>{status}</Badge>;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Health</CardTitle>
        <CardDescription>Bridge job status and user lookup</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Bridge Summary */}
        <div className="space-y-2">
          <Label>Bridge Summary</Label>
          {bridgeSummary ? (
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>Total bridges:</span>
                <span className="font-medium">{bridgeSummary.total}</span>
              </div>
              <div className="space-y-1">
                {Object.entries(bridgeSummary.counts_by_status).map(([status, count]) => (
                  <div key={status} className="flex justify-between text-sm">
                    <span className="capitalize">{status}:</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No bridge data available</p>
          )}
        </div>

        {/* User Lookup */}
        <div className="space-y-2">
          <Label>Lookup User Bridge Status</Label>
          <div className="flex gap-2">
            <Input
              placeholder="User ID (UUID)"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleSearch();
                }
              }}
            />
            <Button onClick={handleSearch} disabled={!userId.trim() || bridgeLoading}>
              {bridgeLoading ? "Loading..." : "Check"}
            </Button>
          </div>
        </div>

        {/* Bridge Results */}
        {searchUserId && (
          <div className="space-y-2">
            <Label>Bridge Records</Label>
            {bridgeLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : bridgeData?.bridges && bridgeData.bridges.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>From → To</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Finished</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bridgeData.bridges.map((bridge) => (
                    <TableRow key={bridge.id}>
                      <TableCell>
                        {bridge.from_profile} → {bridge.to_profile}
                      </TableCell>
                      <TableCell>{getStatusBadge(bridge.status)}</TableCell>
                      <TableCell>
                        {bridge.finished_at
                          ? formatDistanceToNow(new Date(bridge.finished_at), { addSuffix: true })
                          : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground">
                No bridge record found. Will bridge lazily on next learning request.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
