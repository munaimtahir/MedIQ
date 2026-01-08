"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Theme, Block } from "@/lib/api";
import { Play, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface ThemeHeaderProps {
  theme: Theme;
  block: Block;
  yearName: string;
  isAllowed?: boolean; // Deprecated - always true now
  status?: "not_started" | "in_progress" | "completed" | "not_available";
}

export function ThemeHeader({
  theme,
  block,
  yearName,
  isAllowed,
  status = "not_available",
}: ThemeHeaderProps) {
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
        <Link
          href={`/student/blocks/${block.id}`}
          className="hover:text-foreground"
        >
          Block {block.code}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">{theme.title}</span>
      </div>

      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{theme.title}</h1>
          <p className="text-muted-foreground mt-1">
            Theme in Block {block.code} · {yearName}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant={statusVariants[status]}>
            {statusLabels[status]}
          </Badge>
          <Button
            variant="default"
            onClick={() => {
              router.push(
                `/student/practice/build?mode=tutor&theme_ids=${theme.id}`
              );
            }}
          >
            <Play className="mr-2 h-4 w-4" />
            Practice this theme
          </Button>
        </div>
      </div>
    </div>
  );
}
