"use client";

import { useState } from "react";
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
import { Search } from "lucide-react";
import { notify } from "@/lib/notify";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { formatDistanceToNow } from "@/lib/dateUtils";

export function BridgeLookupPanel() {
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(false);
  const [bridgeData, setBridgeData] = useState<{
    bridges?: Array<{
      id: string;
      from_profile: string;
      to_profile: string;
      status: string;
      started_at: string | null;
      finished_at: string | null;
      details: Record<string, unknown> | null;
    }>;
  } | null>(null);

  const handleLookup = async () => {
    if (!userId.trim()) {
      notify.error("User ID required", "Please enter a user ID");
      return;
    }

    setLoading(true);
    try {
      const result = await adminLearningOpsAPI.fetchBridgeStatus({ user_id: userId.trim() });
      setBridgeData(result);
    } catch (error) {
      notify.error("Lookup failed", error instanceof Error ? error.message : "Unknown error");
      setBridgeData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>User Bridge Lookup</CardTitle>
        <CardDescription>Check algorithm state bridge status for a specific user</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <div className="flex-1 space-y-2">
            <Label htmlFor="user-id">User ID</Label>
            <Input
              id="user-id"
              placeholder="Enter user UUID..."
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleLookup();
                }
              }}
            />
          </div>
          <div className="flex items-end">
            <Button onClick={handleLookup} disabled={loading || !userId.trim()}>
              <Search className="mr-2 h-4 w-4" />
              Check
            </Button>
          </div>
        </div>

        {bridgeData && (
          <div className="rounded-md border">
            {bridgeData.bridges && bridgeData.bridges.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>From</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Finished</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bridgeData.bridges.map((bridge) => (
                    <TableRow key={bridge.id}>
                      <TableCell>
                        <Badge variant="secondary">{bridge.from_profile}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{bridge.to_profile}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            bridge.status === "done"
                              ? "default"
                              : bridge.status === "failed"
                                ? "destructive"
                                : "secondary"
                          }
                        >
                          {bridge.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {bridge.started_at
                          ? formatDistanceToNow(new Date(bridge.started_at), { addSuffix: true })
                          : "—"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {bridge.finished_at
                          ? formatDistanceToNow(new Date(bridge.finished_at), { addSuffix: true })
                          : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="p-4 text-center text-muted-foreground">
                No bridge records found for this user
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
