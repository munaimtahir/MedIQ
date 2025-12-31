"use client";

import { cn } from "@/lib/utils";

interface SkeletonCardGridProps {
  cards?: number;
  className?: string;
}

export function SkeletonCardGrid({ cards = 6, className }: SkeletonCardGridProps) {
  return (
    <div
      className={cn(
        "grid gap-4 md:grid-cols-2 lg:grid-cols-3",
        className
      )}
    >
      {Array.from({ length: cards }).map((_, i) => (
        <div
          key={`card-${i}`}
          className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="space-y-4">
            {/* Title */}
            <div className="h-5 w-3/4 animate-pulse rounded bg-slate-200" />
            {/* Description */}
            <div className="space-y-2">
              <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-slate-200" />
            </div>
            {/* Button */}
            <div className="h-9 w-24 animate-pulse rounded-md bg-slate-200" />
          </div>
        </div>
      ))}
    </div>
  );
}

