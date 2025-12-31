"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title: string;
  description?: string;
  errorCode?: string | number;
  actionLabel?: string;
  onAction?: () => void;
  variant?: "page" | "card" | "inline";
  showSupportHint?: boolean;
  className?: string;
}

export function ErrorState({
  title,
  description,
  errorCode,
  actionLabel = "Try again",
  onAction,
  variant = "page",
  showSupportHint = false,
  className,
}: ErrorStateProps) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-4 text-center">
      <AlertCircle
        className={cn(
          "text-red-600",
          variant === "page" ? "h-12 w-12" : variant === "card" ? "h-10 w-10" : "h-8 w-8"
        )}
        aria-hidden="true"
      />
      <div>
        <h3
          className={cn(
            "font-semibold text-slate-900",
            variant === "page" ? "text-xl" : variant === "card" ? "text-lg" : "text-base"
          )}
        >
          {title}
        </h3>
        {description && (
          <p
            className={cn(
              "mt-2 text-slate-600",
              variant === "page" ? "text-base" : "text-sm"
            )}
          >
            {description}
          </p>
        )}
        {errorCode && (
          <p className="mt-1 text-xs text-slate-500">Error code: {errorCode}</p>
        )}
        {showSupportHint && (
          <p className="mt-3 text-sm text-slate-600">
            If this problem persists, please{" "}
            <a href="/support" className="text-primary hover:underline">
              contact support
            </a>
            .
          </p>
        )}
      </div>
      {onAction && (
        <div className="mt-2">
          <Button onClick={onAction} variant="default">
            <RefreshCw className="mr-2 h-4 w-4" />
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );

  if (variant === "page") {
    return (
      <div
        className={cn(
          "flex min-h-[60vh] items-center justify-center",
          className
        )}
        role="alert"
        aria-live="assertive"
      >
        <div className="mx-auto max-w-xl px-4">{content}</div>
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div
        className={cn("flex items-center justify-center py-12", className)}
        role="alert"
        aria-live="assertive"
      >
        {content}
      </div>
    );
  }

  return (
    <div
      className={cn("flex items-center justify-center py-8", className)}
      role="alert"
      aria-live="assertive"
    >
      {content}
    </div>
  );
}

