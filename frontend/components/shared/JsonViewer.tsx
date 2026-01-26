"use client";

import * as React from "react";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface JsonViewerProps {
  data: unknown;
  title?: string;
  defaultExpanded?: boolean;
  className?: string;
  maxHeight?: string;
}

export function JsonViewer({
  data,
  title,
  defaultExpanded = false,
  className,
  maxHeight = "32rem",
}: JsonViewerProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const jsonString = React.useMemo(() => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data]);

  return (
    <div className={cn("rounded-md border bg-muted/50", className)}>
      {title && (
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-semibold hover:bg-muted/80"
        >
          <span>{title}</span>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      )}
      {(isExpanded || !title) && (
        <div
          className="overflow-auto p-3 text-xs font-mono"
          style={{ maxHeight }}
        >
          <pre className="whitespace-pre-wrap break-words">{jsonString}</pre>
        </div>
      )}
    </div>
  );
}
