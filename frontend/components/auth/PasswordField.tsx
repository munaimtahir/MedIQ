"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface PasswordFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  helperText?: string;
  className?: string;
  autoComplete?: string;
  disabled?: boolean;
}

export function PasswordField({
  id,
  label,
  value,
  onChange,
  placeholder = "Enter password",
  error,
  helperText,
  className,
  autoComplete = "current-password",
  disabled = false,
}: PasswordFieldProps) {
  const [showPassword, setShowPassword] = React.useState(false);

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={id} className="text-slate-700 font-medium">
        {label}
      </Label>
      <div className="relative">
        <Input
          id={id}
          type={showPassword ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          disabled={disabled}
          className={cn(
            "pr-10 h-11 rounded-lg border-slate-200 bg-white focus:border-primary focus:ring-primary",
            error && "border-red-500 focus:border-red-500 focus:ring-red-500",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
      {helperText && !error && (
        <p className="text-xs text-slate-500">{helperText}</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
