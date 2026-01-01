"use client";

import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface OnboardingWizardShellProps {
  children: React.ReactNode;
  currentStep: number;
  totalSteps: number;
  stepLabels?: string[];
  className?: string;
}

export function OnboardingWizardShell({
  children,
  currentStep,
  totalSteps,
  stepLabels,
  className,
}: OnboardingWizardShellProps) {
  return (
    <div
      className={cn(
        "min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30",
        className
      )}
    >
      {/* Top Bar */}
      <div className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur-sm">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
                <span className="text-sm font-bold text-white">E</span>
              </div>
              <span className="font-semibold text-slate-900">Exam Prep</span>
            </Link>

            {/* Progress indicator */}
            <div className="hidden sm:flex items-center gap-2">
              {Array.from({ length: totalSteps }).map((_, index) => (
                <React.Fragment key={index}>
                  <StepIndicator
                    step={index + 1}
                    label={stepLabels?.[index]}
                    isActive={currentStep === index + 1}
                    isCompleted={currentStep > index + 1}
                  />
                  {index < totalSteps - 1 && (
                    <div
                      className={cn(
                        "h-0.5 w-8 transition-colors duration-300",
                        currentStep > index + 1 ? "bg-primary" : "bg-slate-200"
                      )}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>

            {/* Mobile progress */}
            <div className="sm:hidden flex items-center gap-2">
              <span className="text-sm font-medium text-slate-600">
                Step {currentStep} of {totalSteps}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">{children}</div>
      </div>
    </div>
  );
}

interface StepIndicatorProps {
  step: number;
  label?: string;
  isActive: boolean;
  isCompleted: boolean;
}

function StepIndicator({
  step,
  label,
  isActive,
  isCompleted,
}: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-medium transition-all duration-300",
          isCompleted && "border-primary bg-primary text-white",
          isActive && !isCompleted && "border-primary text-primary bg-primary/5",
          !isActive && !isCompleted && "border-slate-300 text-slate-400"
        )}
      >
        {isCompleted ? <Check className="h-4 w-4" /> : step}
      </div>
      {label && (
        <span
          className={cn(
            "hidden lg:block text-sm font-medium transition-colors",
            isActive || isCompleted ? "text-slate-900" : "text-slate-400"
          )}
        >
          {label}
        </span>
      )}
    </div>
  );
}

// Progress bar variant for simpler UI
interface ProgressBarProps {
  currentStep: number;
  totalSteps: number;
  className?: string;
}

export function OnboardingProgressBar({
  currentStep,
  totalSteps,
  className,
}: ProgressBarProps) {
  const progress = ((currentStep - 1) / (totalSteps - 1)) * 100;

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex justify-between text-sm text-slate-600">
        <span>Step {currentStep} of {totalSteps}</span>
        <span>{Math.round(progress)}% complete</span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
