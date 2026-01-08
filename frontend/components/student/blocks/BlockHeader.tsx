"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Block } from "@/lib/api";
import { Play, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface BlockHeaderProps {
  block: Block;
  yearName: string;
  isAllowed?: boolean; // Deprecated - always true now
  status?: "not_started" | "in_progress" | "completed" | "not_available";
}

export function BlockHeader({ 
  block, 
  yearName, 
  isAllowed: _isAllowed, // eslint-disable-line @typescript-eslint/no-unused-vars
  status = "not_available" 
}: BlockHeaderProps) {
  const router = useRouter();

  const statusLabels = {
    not_started: "Not started",
    in_progress: "In progress",
    completed: "Completed",
    not_available: "Not available yet",
  };

  const statusVariants = {
    not_started: "secondary",
    in_progress: "default",
    completed: "default",
    not_available: "secondary",
  } as const;

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student/blocks" className="hover:text-foreground">
          Blocks
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">Block {block.code}</span>
      </div>

      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Block {block.code}</h1>
          <p className="text-muted-foreground mt-1">
            Part of {yearName} curriculum
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant={statusVariants[status]} title={
            status === "not_available"
              ? "Progress will appear after the test engine is enabled"
              : undefined
          }>
            {statusLabels[status]}
          </Badge>
          <Button
            variant="default"
            onClick={() => {
              router.push(`/student/practice/build?block_ids=${block.id}`);
            }}
          >
            <Play className="mr-2 h-4 w-4" />
            Practice entire block
          </Button>
        </div>
      </div>
    </div>
  );
}
