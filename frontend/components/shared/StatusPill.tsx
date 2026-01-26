"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type StatusValue = "UP" | "DOWN" | "SHADOW" | "ACTIVE" | "DISABLED" | string;

interface StatusPillProps {
  status: StatusValue;
  label?: string;
  className?: string;
}

const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  UP: "default",
  DOWN: "destructive",
  SHADOW: "secondary",
  ACTIVE: "default",
  DISABLED: "outline",
  active: "default",
  shadow: "secondary",
  disabled: "outline",
  v1: "default",
  v0: "outline",
};

export function StatusPill({ status, label, className }: StatusPillProps) {
  const displayLabel = label || status;
  const variant = statusVariants[status] || "secondary";

  return (
    <Badge
      variant={variant}
      className={cn(
        variant === "default" && status === "UP" && "bg-green-600",
        variant === "default" && status === "ACTIVE" && "bg-green-600",
        variant === "default" && status === "active" && "bg-green-600",
        variant === "default" && status === "v1" && "bg-green-600",
        className,
      )}
    >
      {displayLabel}
    </Badge>
  );
}
