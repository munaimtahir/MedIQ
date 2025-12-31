"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingStateProps {
  title?: string;
  description?: string;
  variant?: "page" | "section" | "inline";
  icon?: React.ReactNode;
  className?: string;
}

export function LoadingState({
  title = "Loading…",
  description,
  variant = "page",
  icon,
  className,
}: LoadingStateProps) {
  const defaultIcon = (
    <Loader2
      className={cn(
        "animate-spin text-primary",
        variant === "page" ? "h-8 w-8" : variant === "section" ? "h-6 w-6" : "h-4 w-4"
      )}
      aria-hidden="true"
    />
  );

  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      {icon || defaultIcon}
      <div className="text-center">
        <h3
          className={cn(
            "font-semibold text-slate-900",
            variant === "page" ? "text-xl" : variant === "section" ? "text-lg" : "text-sm"
          )}
        >
          {title}
        </h3>
        {description && (
          <p
            className={cn(
              "mt-1 text-slate-600",
              variant === "page" ? "text-base" : variant === "section" ? "text-sm" : "text-xs"
            )}
          >
            {description}
          </p>
        )}
      </div>
    </div>
  );

  if (variant === "page") {
    return (
      <div
        className={cn(
          "flex min-h-[60vh] items-center justify-center",
          className
        )}
        role="status"
        aria-live="polite"
        aria-label={title}
      >
        <div className="mx-auto max-w-xl px-4 text-center">{content}</div>
      </div>
    );
  }

  if (variant === "section") {
    return (
      <div
        className={cn("flex items-center justify-center py-12", className)}
        role="status"
        aria-live="polite"
        aria-label={title}
      >
        {content}
      </div>
    );
  }

  return (
    <div
      className={cn("flex items-center justify-center py-4", className)}
      role="status"
      aria-live="polite"
      aria-label={title}
    >
      {content}
    </div>
  );
}

