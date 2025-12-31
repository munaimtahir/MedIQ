"use client";

import { cn } from "@/lib/utils";

interface SkeletonTableProps {
  rows?: number;
  cols?: number;
  className?: string;
}

export function SkeletonTable({ rows = 6, cols = 5, className }: SkeletonTableProps) {
  return (
    <div className={cn("w-full", className)}>
      <div className="space-y-3">
        {/* Header */}
        <div className="flex gap-4 border-b border-slate-200 pb-3">
          {Array.from({ length: cols }).map((_, i) => (
            <div
              key={`header-${i}`}
              className="h-4 w-24 animate-pulse rounded bg-slate-200"
            />
          ))}
        </div>
        {/* Rows */}
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={`row-${rowIndex}`} className="flex gap-4 py-3">
            {Array.from({ length: cols }).map((_, colIndex) => (
              <div
                key={`cell-${rowIndex}-${colIndex}`}
                className={cn(
                  "h-4 animate-pulse rounded bg-slate-200",
                  colIndex === 0 ? "w-16" : colIndex === cols - 1 ? "w-32" : "w-24"
                )}
                style={{
                  animationDelay: `${(rowIndex * cols + colIndex) * 50}ms`,
                }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

