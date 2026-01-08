"use client";

import * as React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  actionHref?: string;
  icon?: React.ReactNode;
  variant?: "page" | "card" | "inline";
  className?: string;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  icon,
  variant = "page",
  className,
}: EmptyStateProps) {
  const defaultIcon = icon || (
    <Inbox className={cn("text-slate-400", variant === "page" ? "h-12 w-12" : "h-8 w-8")} />
  );

  const content = (
    <div className="flex flex-col items-center justify-center gap-4 text-center">
      <div className="flex items-center justify-center">{defaultIcon}</div>
      <div>
        <h3
          className={cn(
            "font-semibold text-slate-900",
            variant === "page" ? "text-xl" : variant === "card" ? "text-lg" : "text-base",
          )}
        >
          {title}
        </h3>
        {description && (
          <p className={cn("mt-2 text-slate-600", variant === "page" ? "text-base" : "text-sm")}>
            {description}
          </p>
        )}
      </div>
      {actionLabel && (onAction || actionHref) && (
        <div className="mt-2">
          {actionHref ? (
            <Button asChild>
              <Link href={actionHref}>{actionLabel}</Link>
            </Button>
          ) : (
            <Button onClick={onAction}>{actionLabel}</Button>
          )}
        </div>
      )}
    </div>
  );

  if (variant === "page") {
    return (
      <div
        className={cn("flex min-h-[60vh] items-center justify-center", className)}
        role="status"
        aria-live="polite"
      >
        <div className="mx-auto max-w-xl px-4">{content}</div>
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div
        className={cn("flex items-center justify-center py-12", className)}
        role="status"
        aria-live="polite"
      >
        {content}
      </div>
    );
  }

  return (
    <div
      className={cn("flex items-center justify-center py-8", className)}
      role="status"
      aria-live="polite"
    >
      {content}
    </div>
  );
}
