"use client";

import * as React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface InlineNoticeProps {
  variant: "info" | "warning" | "success" | "error";
  title?: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  className?: string;
}

const variantStyles = {
  info: {
    container: "border-blue-200 bg-blue-50 text-blue-900",
    icon: "text-blue-600",
    title: "text-blue-900",
    description: "text-blue-700",
  },
  warning: {
    container: "border-amber-200 bg-amber-50 text-amber-900",
    icon: "text-amber-600",
    title: "text-amber-900",
    description: "text-amber-700",
  },
  success: {
    container: "border-green-200 bg-green-50 text-green-900",
    icon: "text-green-600",
    title: "text-green-900",
    description: "text-green-700",
  },
  error: {
    container: "border-red-200 bg-red-50 text-red-900",
    icon: "text-red-600",
    title: "text-red-900",
    description: "text-red-700",
  },
};

const variantIcons = {
  info: Info,
  warning: AlertTriangle,
  success: CheckCircle2,
  error: AlertCircle,
};

export function InlineNotice({
  variant,
  title,
  description,
  actionLabel,
  actionHref,
  onAction,
  className,
}: InlineNoticeProps) {
  const styles = variantStyles[variant];
  const Icon = variantIcons[variant];

  return (
    <div
      className={cn(
        "rounded-xl border p-4",
        styles.container,
        className
      )}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <Icon className={cn("mt-0.5 h-5 w-5 flex-shrink-0", styles.icon)} aria-hidden="true" />
        <div className="flex-1">
          {title && (
            <h4 className={cn("font-semibold", styles.title)}>{title}</h4>
          )}
          {description && (
            <p className={cn("mt-1 text-sm", styles.description)}>{description}</p>
          )}
          {(actionLabel && (onAction || actionHref)) && (
            <div className="mt-3">
              {actionHref ? (
                <Button asChild variant="outline" size="sm">
                  <Link href={actionHref}>{actionLabel}</Link>
                </Button>
              ) : (
                <Button onClick={onAction} variant="outline" size="sm">
                  {actionLabel}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

