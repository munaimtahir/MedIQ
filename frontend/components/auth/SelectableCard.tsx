"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface SelectableCardProps {
  selected: boolean;
  onClick: () => void;
  title: string;
  description?: string;
  disabled?: boolean;
  className?: string;
  showCheckmark?: boolean;
}

export function SelectableCard({
  selected,
  onClick,
  title,
  description,
  disabled,
  className,
  showCheckmark = true,
}: SelectableCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "group relative w-full rounded-xl border-2 p-4 text-left transition-all duration-200",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
        selected
          ? "border-primary bg-primary/5 shadow-sm"
          : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox indicator */}
        {showCheckmark && (
          <div
            className={cn(
              "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200",
              selected
                ? "border-primary bg-primary text-white"
                : "border-slate-300 bg-white"
            )}
          >
            {selected && <Check className="h-3 w-3" />}
          </div>
        )}

        <div className="flex-1 min-w-0">
          <p
            className={cn(
              "font-medium transition-colors",
              selected ? "text-primary" : "text-slate-900"
            )}
          >
            {title}
          </p>
          {description && (
            <p className="mt-0.5 text-sm text-slate-500">{description}</p>
          )}
        </div>
      </div>
    </button>
  );
}

// Compact version for blocks/subjects
interface SelectableChipProps {
  selected: boolean;
  onClick: () => void;
  label: string;
  disabled?: boolean;
  className?: string;
}

export function SelectableChip({
  selected,
  onClick,
  label,
  disabled,
  className,
}: SelectableChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-2 rounded-lg border-2 px-4 py-2.5 text-sm font-medium transition-all duration-200",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
        selected
          ? "border-primary bg-primary/5 text-primary"
          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
    >
      <div
        className={cn(
          "flex h-4 w-4 items-center justify-center rounded border transition-all duration-200",
          selected
            ? "border-primary bg-primary text-white"
            : "border-slate-300 bg-white"
        )}
      >
        {selected && <Check className="h-3 w-3" />}
      </div>
      {label}
    </button>
  );
}
