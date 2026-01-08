"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Theme, Block } from "@/lib/api";

interface ThemeOverviewCardProps {
  theme: Theme;
  block: Block;
  isAllowed?: boolean; // Deprecated - always true now
}

export function ThemeOverviewCard({ theme, block, isAllowed }: ThemeOverviewCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Theme Overview</CardTitle>
        <CardDescription>Information about this theme</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Description */}
        <div>
          <p className="text-sm text-muted-foreground">
            {theme.description || "Practice questions related to this theme."}
          </p>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Block: </span>
            <span className="font-medium">{block.code}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
