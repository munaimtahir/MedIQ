"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Block } from "@/lib/api";

interface BlockOverviewCardProps {
  block: Block;
  themeCount: number;
  isAllowed?: boolean; // Deprecated - always true now
}

export function BlockOverviewCard({ block: _block, themeCount, isAllowed: _isAllowed }: BlockOverviewCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Block Overview</CardTitle>
        <CardDescription>Information about this block</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Description */}
        <div>
          <p className="text-sm text-muted-foreground">
            Themes and practice options for this block.
          </p>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Themes: </span>
            <span className="font-medium">{themeCount}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
