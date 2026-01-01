"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, XCircle, AlertTriangle, CheckCircle } from "lucide-react";

export interface InlineAlertProps {
  variant?: "error" | "warning" | "success" | "info";
  title?: string;
  message: string;
  className?: string;
  onDismiss?: () => void;
}

const variantConfig = {
  error: {
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-800",
    icon: XCircle,
    iconColor: "text-red-500",
  },
  warning: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-800",
    icon: AlertTriangle,
    iconColor: "text-amber-500",
  },
  success: {
    bg: "bg-green-50",
    border: "border-green-200",
    text: "text-green-800",
    icon: CheckCircle,
    iconColor: "text-green-500",
  },
  info: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-800",
    icon: AlertCircle,
    iconColor: "text-blue-500",
  },
};

export function InlineAlert({
  variant = "error",
  title,
  message,
  className,
  onDismiss,
}: InlineAlertProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-lg border p-3",
        config.bg,
        config.border,
        className
      )}
    >
      <Icon className={cn("h-5 w-5 shrink-0 mt-0.5", config.iconColor)} />
      <div className="flex-1 min-w-0">
        {title && (
          <p className={cn("text-sm font-medium", config.text)}>{title}</p>
        )}
        <p className={cn("text-sm", config.text, title && "mt-0.5")}>
          {message}
        </p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className={cn(
            "shrink-0 rounded p-1 hover:bg-black/5 transition-colors",
            config.text
          )}
          aria-label="Dismiss"
        >
          <XCircle className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
