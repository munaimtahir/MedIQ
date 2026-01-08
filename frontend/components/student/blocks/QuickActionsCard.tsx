"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Play, BarChart3 } from "lucide-react";
import { useRouter } from "next/navigation";

interface QuickActionsCardProps {
  blockId: number;
  yearId: number;
  isBlockAllowed?: boolean; // Deprecated - always true now
  allowedBlockIds?: number[]; // Deprecated - no longer used
}

export function QuickActionsCard({
  blockId,
  yearId,
  isBlockAllowed: _isBlockAllowed, // eslint-disable-line @typescript-eslint/no-unused-vars
  allowedBlockIds: _allowedBlockIds, // eslint-disable-line @typescript-eslint/no-unused-vars
}: QuickActionsCardProps) {
  const router = useRouter();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
        <CardDescription>Common actions for this block</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button
          variant="default"
          className="w-full justify-start"
          onClick={() => {
            router.push(`/student/practice/build?block_ids=${blockId}`);
          }}
        >
          <Play className="mr-2 h-4 w-4" />
          Practice entire block
        </Button>

        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => {
            router.push(`/student/practice/build?year_id=${yearId}`);
          }}
        >
          <Play className="mr-2 h-4 w-4" />
          Start mixed practice (all blocks)
        </Button>

        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => {
            // Placeholder - analytics page not implemented yet
            router.push("/student/analytics");
          }}
        >
          <BarChart3 className="mr-2 h-4 w-4" />
          View analytics
        </Button>
      </CardContent>
    </Card>
  );
}
