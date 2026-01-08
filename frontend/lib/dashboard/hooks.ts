/**
 * Dashboard data fetching hooks.
 */

import { useEffect, useState } from "react";
import { syllabusAPI, onboardingAPI } from "@/lib/api";
import { Year, Block, Theme, UserProfile } from "@/lib/api";
import {
  DashboardVM,
  NextAction,
} from "./types";
import {
  getMockMetrics,
  getMockWeakThemes,
  getMockRecentSessions,
  getMockAnnouncements,
} from "./mock";

interface DashboardDataState {
  data: DashboardVM | null;
  loading: boolean;
  error: Error | null;
}

export function useDashboardData(): DashboardDataState {
  const [state, setState] = useState<DashboardDataState>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        // Load user profile to get selected year
        let profile: UserProfile | null = null;
        try {
          profile = await onboardingAPI.getProfile();
          console.log("[Dashboard] Loaded user profile:", {
            onboarding_completed: profile?.onboarding_completed,
            selected_year: profile?.selected_year?.display_name,
            selected_blocks_count: profile?.selected_blocks?.length || 0,
          });
        } catch (err) {
          console.error("[Dashboard] Failed to load profile:", err);
          // Continue without profile - will use defaults
        }
        
        // Determine year to use
        let selectedYear: Year | null = null;
        let selectedYearName: string | undefined;

        // Load years first
        let years: Year[] = [];
        try {
          years = await syllabusAPI.getYears();
          console.log("[Dashboard] Loaded years:", years.length);
        } catch (err) {
          console.error("[Dashboard] Failed to load years:", err);
          throw new Error(`Failed to load academic years: ${err instanceof Error ? err.message : "Unknown error"}`);
        }
        
        if (years.length === 0) {
          throw new Error("No years available in the system");
        }
        
        // Improved year matching logic
        if (profile?.selected_year) {
          const profileYearName = profile.selected_year.display_name;
          console.log("[Dashboard] User selected year:", profileYearName);
          
          // Try multiple matching strategies
          selectedYear = years.find((y) => {
            // Exact match
            if (y.name === profileYearName) return true;
            // Case-insensitive match
            if (y.name.toLowerCase() === profileYearName.toLowerCase()) return true;
            // Partial match (e.g., "1st Year" matches "1st Year MBBS")
            if (y.name.toLowerCase().includes(profileYearName.toLowerCase()) || 
                profileYearName.toLowerCase().includes(y.name.toLowerCase())) return true;
            // Try matching by removing common suffixes
            const normalizedYear = y.name.toLowerCase().replace(/\s*(mbbs|year|yr)\s*/gi, "").trim();
            const normalizedProfile = profileYearName.toLowerCase().replace(/\s*(mbbs|year|yr)\s*/gi, "").trim();
            if (normalizedYear === normalizedProfile) return true;
            return false;
          }) || null;
          
          if (!selectedYear) {
            console.warn("[Dashboard] Could not match user's year, using first available year");
          }
        }
        
        // Fallback to first year if no match found
        if (!selectedYear) {
          selectedYear = years[0] || null;
        }

        if (!selectedYear) {
          throw new Error("No years available");
        }

        const selectedYearId = selectedYear.id;
        selectedYearName = selectedYear.name;
        console.log("[Dashboard] Using year:", selectedYearName, "(ID:", selectedYearId, ")");

        // Load blocks for selected year
        let blocks: Block[] = [];
        try {
          blocks = await syllabusAPI.getBlocks(selectedYearName);
          console.log("[Dashboard] Loaded blocks:", blocks.length);
        } catch (err) {
          console.error("[Dashboard] Failed to load blocks:", err);
          throw new Error(`Failed to load blocks for ${selectedYearName}: ${err instanceof Error ? err.message : "Unknown error"}`);
        }

        // Load themes for first block (for dropdown)
        const themesByBlock: Record<number, Theme[]> = {};
        if (blocks.length > 0) {
          try {
            const firstBlockThemes = await syllabusAPI.getThemes(blocks[0].id);
            themesByBlock[blocks[0].id] = firstBlockThemes;
            console.log("[Dashboard] Loaded themes for first block:", firstBlockThemes.length);
          } catch (err) {
            console.warn("[Dashboard] Failed to load themes for first block:", err);
            // Non-critical, continue without themes
          }
        }

        // Load mock data for features not yet implemented
        const recentSessions = getMockRecentSessions();
        const unfinishedSession = recentSessions.find((s) => s.status === "in_progress");

        // Determine next action
        const nextAction = determineNextAction(
          profile,
          unfinishedSession,
          blocks,
          themesByBlock
        );

        // Load metrics (mock for now)
        const metrics = getMockMetrics();

        // Load weak themes (mock for now)
        const weakThemes = getMockWeakThemes();

        // Load announcements (mock for now)
        const announcements = getMockAnnouncements();

        if (cancelled) return;

        setState({
          data: {
            user: {
              name: undefined, // Could be added from profile later
              yearName: selectedYearName,
              yearId: selectedYearId,
            },
            blocks,
            themesByBlock,
            nextAction,
            metrics,
            weakThemes,
            recentSessions,
            announcements,
            hasUnfinishedSession: !!unfinishedSession,
            unfinishedSession,
          },
          loading: false,
          error: null,
        });
      } catch (error) {
        if (cancelled) return;
        const errorMessage = error instanceof Error ? error.message : "Failed to load dashboard";
        console.error("[Dashboard] Error loading dashboard:", error);
        setState({
          data: null,
          loading: false,
          error: error instanceof Error ? error : new Error(errorMessage),
        });
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

function determineNextAction(
  profile: UserProfile | null,
  unfinishedSession: RecentSession | undefined,
  blocks: Block[],
  themesByBlock: Record<number, Theme[]>
): NextAction {
  console.log("[Dashboard] determineNextAction called with:", {
    profile_exists: !!profile,
    onboarding_completed: profile?.onboarding_completed,
    has_unfinished_session: !!unfinishedSession,
    blocks_count: blocks.length,
  });

  // If onboarding not completed
  if (!profile?.onboarding_completed) {
    console.log("[Dashboard] Onboarding not completed, showing onboarding prompt");
    return {
      type: "onboarding",
      label: "Complete Onboarding",
      href: "/onboarding",
      hint: "Select your year and blocks to get started",
    };
  }

  // If there's an unfinished session, prioritize resume
  if (unfinishedSession) {
    const firstBlock = blocks[0];
    const firstBlockThemes = themesByBlock[firstBlock?.id || 0] || [];
    const firstTheme = firstBlockThemes[0];

    return {
      type: "resume",
      label: "Resume Session",
      href: unfinishedSession.href,
      hint: unfinishedSession.title,
      secondaryActions: [
        {
          label: "Start Quick Practice",
          href: "/student/practice/build?preset=quick",
        },
        {
          label: "Build Custom Practice",
          href: "/student/practice/build",
        },
      ],
    };
  }

  // Default: quick practice
  const firstBlock = blocks.length > 0 ? blocks[0] : null;
  const firstBlockThemes = firstBlock ? (themesByBlock[firstBlock.id] || []) : [];
  const firstTheme = firstBlockThemes.length > 0 ? firstBlockThemes[0] : null;

  return {
    type: "quick_practice",
    label: "Start Quick Practice",
    href: "/student/practice/build?preset=quick",
    hint: firstBlock && firstTheme
      ? `Suggested: Block ${firstBlock.code} → Theme: ${firstTheme.title} (10 questions)`
      : blocks.length > 0
      ? "Start your first practice session"
      : "Complete onboarding to select blocks and start practicing",
    secondaryActions: [
      {
        label: "Build Custom Practice",
        href: "/student/practice/build",
      },
    ],
  };
}
