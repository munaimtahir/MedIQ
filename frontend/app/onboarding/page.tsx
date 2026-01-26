"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { authClient, type User } from "@/lib/authClient";
import { onboardingAPI, type OnboardingYearOption } from "@/lib/api";
import { useUserStore, selectFetchUser } from "@/store/userStore";
import { OnboardingWizardShell } from "@/components/auth/OnboardingWizardShell";
import { StepContainer } from "@/components/auth/StepContainer";
import { SelectableCard, SelectableChip } from "@/components/auth/SelectableCard";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { Button } from "@/components/ui/button";
import { Loader2, ArrowLeft, ArrowRight, Check, RefreshCw } from "lucide-react";

type Step = 1 | 2 | 3;

interface OnboardingState {
  yearId: number | null;
  blockIds: Set<number>;
  subjectIds: Set<number>;
}

export default function OnboardingPage() {
  const router = useRouter();
  const contentRef = useRef<HTMLDivElement>(null);
  const fetchUser = useUserStore(selectFetchUser);

  // Data state
  const [years, setYears] = useState<OnboardingYearOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step state
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");

  // Selection state
  const [selections, setSelections] = useState<OnboardingState>({
    yearId: null,
    blockIds: new Set(),
    subjectIds: new Set(),
  });

  // Year change notification
  const [yearChangeNote, setYearChangeNote] = useState(false);

  // Derived data
  const selectedYear = years.find((y) => y.id === selections.yearId);
  const availableBlocks = selectedYear?.blocks || [];
  const availableSubjects = selectedYear?.subjects || [];
  const hasSubjects = availableSubjects.length > 0;

  // Total steps depends on whether subjects exist
  const totalSteps = hasSubjects ? 3 : 2;
  const stepLabels = hasSubjects
    ? ["Select Year", "Select Blocks", "Confirm Subjects"]
    : ["Select Year", "Select Blocks"];

  // Check auth and onboarding status
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const result = await authClient.me();
        if (!result.data?.user) {
          // Not authenticated
          router.push("/login");
          return;
        }

        const user = result.data.user as User;
        if (user.onboarding_completed) {
          // Already onboarded, redirect based on role
          if (user.role === "ADMIN" || user.role === "REVIEWER") {
            router.push("/admin");
          } else {
            router.push("/student/dashboard");
          }
          return;
        }

        // Load onboarding options
        await loadOptions();
      } catch {
        router.push("/login");
      }
    };
    checkAuth();
  }, [router]);

  const loadOptions = async () => {
    try {
      setLoading(true);
      setError(null);
      const options = await onboardingAPI.getOptions();
      setYears(options.years);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load options";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // When year changes, auto-select all blocks
  useEffect(() => {
    if (selectedYear) {
      const allBlockIds = new Set(selectedYear.blocks.map((b) => b.id));
      const allSubjectIds = new Set(selectedYear.subjects.map((s) => s.id));
      setSelections((prev) => ({
        ...prev,
        blockIds: allBlockIds,
        subjectIds: allSubjectIds,
      }));
    }
  }, [selectedYear]);

  // Handle year selection
  const handleYearSelect = (yearId: number) => {
    if (selections.yearId !== null && selections.yearId !== yearId) {
      // Changing year - show notification
      setYearChangeNote(true);
      setTimeout(() => setYearChangeNote(false), 3000);
    }
    setSelections((prev) => ({
      ...prev,
      yearId,
      blockIds: new Set(),
      subjectIds: new Set(),
    }));
  };

  // Handle block toggle
  const handleBlockToggle = (blockId: number) => {
    setSelections((prev) => {
      const newBlocks = new Set(prev.blockIds);
      if (newBlocks.has(blockId)) {
        newBlocks.delete(blockId);
      } else {
        newBlocks.add(blockId);
      }
      return { ...prev, blockIds: newBlocks };
    });
  };

  // Handle subject toggle
  const handleSubjectToggle = (subjectId: number) => {
    setSelections((prev) => {
      const newSubjects = new Set(prev.subjectIds);
      if (newSubjects.has(subjectId)) {
        newSubjects.delete(subjectId);
      } else {
        newSubjects.add(subjectId);
      }
      return { ...prev, subjectIds: newSubjects };
    });
  };

  // Select/deselect all blocks
  const toggleAllBlocks = () => {
    setSelections((prev) => {
      if (prev.blockIds.size === availableBlocks.length) {
        return { ...prev, blockIds: new Set() };
      }
      return { ...prev, blockIds: new Set(availableBlocks.map((b) => b.id)) };
    });
  };

  // Navigation
  const canContinue = useCallback((): boolean => {
    switch (currentStep) {
      case 1:
        return selections.yearId !== null;
      case 2:
        return selections.blockIds.size > 0;
      case 3:
        return true; // Subjects are optional/read-only
      default:
        return false;
    }
  }, [currentStep, selections]);

  const goNext = () => {
    if (!canContinue()) return;

    setDirection("forward");

    if (currentStep === 1) {
      setCurrentStep(2);
    } else if (currentStep === 2) {
      if (hasSubjects) {
        setCurrentStep(3);
      } else {
        handleSubmit();
      }
    } else if (currentStep === 3) {
      handleSubmit();
    }
  };

  const goBack = () => {
    setDirection("backward");

    if (currentStep === 2) {
      setCurrentStep(1);
    } else if (currentStep === 3) {
      setCurrentStep(2);
    }
  };

  // Submit onboarding
  const handleSubmit = async () => {
    if (!selections.yearId || selections.blockIds.size === 0) {
      setError("Please select a year and at least one block.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      await onboardingAPI.submitOnboarding({
        year_id: selections.yearId,
        block_ids: Array.from(selections.blockIds),
        subject_ids: selections.subjectIds.size > 0 ? Array.from(selections.subjectIds) : undefined,
      });

      // Refresh user store to get updated onboarding status
      await fetchUser();

      // Success - route to dashboard
      router.push("/student/dashboard");
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to save preferences";
      setError(errorMessage);
      setSubmitting(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <OnboardingWizardShell currentStep={1} totalSteps={3}>
        <div className="flex items-center justify-center py-24">
          <div className="text-center">
            <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
            <p className="text-slate-600">Loading your options...</p>
          </div>
        </div>
      </OnboardingWizardShell>
    );
  }

  // Error state (initial load failed)
  if (error && years.length === 0) {
    return (
      <OnboardingWizardShell currentStep={1} totalSteps={3}>
        <div className="mx-auto max-w-md py-12">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <RefreshCw className="h-6 w-6 text-red-600" />
            </div>
            <h2 className="mb-2 text-xl font-semibold text-slate-900">Unable to load options</h2>
            <p className="mb-6 text-slate-600">{error}</p>
            <Button onClick={loadOptions} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try again
            </Button>
          </div>
        </div>
      </OnboardingWizardShell>
    );
  }

  return (
    <OnboardingWizardShell
      currentStep={currentStep}
      totalSteps={totalSteps}
      stepLabels={stepLabels}
    >
      <div ref={contentRef} className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        {/* Step Content */}
        <div className="p-8">
          <StepContainer stepKey={currentStep} direction={direction}>
            {/* Step 1: Select Year */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    Choose your academic year
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    This helps us set up your blocks and subjects.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {years.map((year) => (
                    <SelectableCard
                      key={year.id}
                      selected={selections.yearId === year.id}
                      onClick={() => handleYearSelect(year.id)}
                      title={year.display_name}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Step 2: Select Blocks */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold text-slate-900">Select your blocks</h2>
                    <p className="mt-1 text-sm text-slate-500">
                      These blocks will organize your practice and revision.
                    </p>
                  </div>
                  {selectedYear && (
                    <span className="inline-flex shrink-0 items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                      {selectedYear.display_name}
                    </span>
                  )}
                </div>

                {yearChangeNote && (
                  <InlineAlert
                    variant="info"
                    message="Blocks updated for your new year selection."
                    onDismiss={() => setYearChangeNote(false)}
                  />
                )}

                {availableBlocks.length === 0 ? (
                  <InlineAlert
                    variant="warning"
                    message="No blocks are available for this year. Please contact your administrator."
                  />
                ) : (
                  <>
                    <div className="flex justify-end">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={toggleAllBlocks}
                        className="text-sm"
                      >
                        {selections.blockIds.size === availableBlocks.length
                          ? "Clear all"
                          : "Select all"}
                      </Button>
                    </div>

                    <div className="flex flex-wrap gap-3">
                      {availableBlocks.map((block) => (
                        <SelectableChip
                          key={block.id}
                          selected={selections.blockIds.has(block.id)}
                          onClick={() => handleBlockToggle(block.id)}
                          label={block.display_name}
                        />
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Step 3: Confirm Subjects */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">Confirm your subjects</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    These are set for your year. You can update later if needed.
                  </p>
                </div>

                {availableSubjects.length === 0 ? (
                  <InlineAlert
                    variant="info"
                    message="No subjects are configured for this year yet."
                  />
                ) : (
                  <div className="flex flex-wrap gap-3">
                    {availableSubjects.map((subject) => (
                      <SelectableChip
                        key={subject.id}
                        selected={selections.subjectIds.has(subject.id)}
                        onClick={() => handleSubjectToggle(subject.id)}
                        label={subject.display_name}
                      />
                    ))}
                  </div>
                )}

                {/* Summary */}
                <div className="space-y-2 rounded-lg bg-slate-50 p-4">
                  <h3 className="text-sm font-medium text-slate-900">Summary</h3>
                  <div className="space-y-1 text-sm text-slate-600">
                    <p>
                      <span className="font-medium">Year:</span> {selectedYear?.display_name}
                    </p>
                    <p>
                      <span className="font-medium">Blocks:</span> {selections.blockIds.size}{" "}
                      selected
                    </p>
                    {hasSubjects && (
                      <p>
                        <span className="font-medium">Subjects:</span> {selections.subjectIds.size}{" "}
                        selected
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </StepContainer>

          {/* Error */}
          {error && (
            <div className="mt-6">
              <InlineAlert variant="error" message={error} onDismiss={() => setError(null)} />
            </div>
          )}
        </div>

        {/* Footer with navigation */}
        <div className="rounded-b-2xl border-t border-slate-100 bg-slate-50/50 px-8 py-4">
          <div className="flex items-center justify-between">
            {/* Back button */}
            <div>
              {currentStep > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={goBack}
                  disabled={submitting}
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
              )}
            </div>

            {/* Continue / Finish button */}
            <Button
              type="button"
              onClick={goNext}
              disabled={!canContinue() || submitting}
              className="min-w-[140px] gap-2"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : currentStep === totalSteps ? (
                <>
                  <Check className="h-4 w-4" />
                  Finish setup
                </>
              ) : (
                <>
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </OnboardingWizardShell>
  );
}
