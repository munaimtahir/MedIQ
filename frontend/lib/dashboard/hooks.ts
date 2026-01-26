/**
 * Dashboard data fetching hooks.
 */

import { useEffect, useState, useMemo } from "react";
import { syllabusAPI, onboardingAPI } from "@/lib/api";
import { Year, Block, Theme, UserProfile } from "@/lib/api";
import { DashboardVM, NextAction, RecentSession, DashboardMetrics, WeakTheme } from "./types";
import {
  getEmptyMetrics,
  getEmptyWeakThemes,
  getEmptyRecentSessions,
  getEmptyAnnouncements,
} from "./mock";
import { logger } from "@/lib/logger";
import { getOverview, getRecentSessions, type RecentSessionSummary } from "@/lib/api/analyticsApi";

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
          logger.log("[Dashboard] Loaded user profile:", {
            onboarding_completed: profile?.onboarding_completed,
            selected_year: profile?.selected_year?.display_name,
            selected_blocks_count: profile?.selected_blocks?.length || 0,
          });
        } catch (err) {
          logger.error("[Dashboard] Failed to load profile:", err);
          // Continue without profile - will use defaults
        }

        // Determine year to use
        let selectedYear: Year | null = null;

        // Load years first
        let years: Year[] = [];
        try {
          years = await syllabusAPI.getYears();
          logger.log("[Dashboard] Loaded years:", years.length);
        } catch (err) {
          logger.error("[Dashboard] Failed to load years:", err);
          throw new Error(
            `Failed to load academic years: ${err instanceof Error ? err.message : "Unknown error"}`,
          );
        }

        if (years.length === 0) {
          throw new Error("No years available in the system");
        }

        // Improved year matching logic
        if (profile?.selected_year) {
          const profileYearName = profile.selected_year.display_name;
          logger.log("[Dashboard] User selected year:", profileYearName);

          // Try multiple matching strategies
          selectedYear =
            years.find((y) => {
              // Exact match
              if (y.name === profileYearName) return true;
              // Case-insensitive match
              if (y.name.toLowerCase() === profileYearName.toLowerCase()) return true;
              // Partial match (e.g., "1st Year" matches "1st Year MBBS")
              if (
                y.name.toLowerCase().includes(profileYearName.toLowerCase()) ||
                profileYearName.toLowerCase().includes(y.name.toLowerCase())
              )
                return true;
              // Try matching by removing common suffixes
              const normalizedYear = y.name
                .toLowerCase()
                .replace(/\s*(mbbs|year|yr)\s*/gi, "")
                .trim();
              const normalizedProfile = profileYearName
                .toLowerCase()
                .replace(/\s*(mbbs|year|yr)\s*/gi, "")
                .trim();
              if (normalizedYear === normalizedProfile) return true;
              return false;
            }) || null;

          if (!selectedYear) {
            logger.warn("[Dashboard] Could not match user's year, using first available year");
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
        const selectedYearName = selectedYear.name;
        logger.log("[Dashboard] Using year:", selectedYearName, "(ID:", selectedYearId, ")");

        // Load blocks for selected year
        let blocks: Block[] = [];
        try {
          blocks = await syllabusAPI.getBlocks(selectedYearName);
          logger.log("[Dashboard] Loaded blocks:", blocks.length);
        } catch (err) {
          logger.error("[Dashboard] Failed to load blocks:", err);
          throw new Error(
            `Failed to load blocks for ${selectedYearName}: ${err instanceof Error ? err.message : "Unknown error"}`,
          );
        }

        // Load themes for first block (for dropdown)
        const themesByBlock: Record<number, Theme[]> = {};
        if (blocks.length > 0) {
          try {
            const firstBlockThemes = await syllabusAPI.getThemes(blocks[0].id);
            themesByBlock[blocks[0].id] = firstBlockThemes;
            logger.log("[Dashboard] Loaded themes for first block:", firstBlockThemes.length);
          } catch (err) {
            logger.warn("[Dashboard] Failed to load themes for first block:", err);
            // Non-critical, continue without themes
          }
        }

        // Load real analytics data
        let analyticsOverview = null;
        let recentSessionsData: RecentSessionSummary[] = [];
        try {
          analyticsOverview = await getOverview();
          logger.log("[Dashboard] Loaded analytics overview:", {
            sessions_completed: analyticsOverview.sessions_completed,
            questions_answered: analyticsOverview.questions_answered,
            accuracy_pct: analyticsOverview.accuracy_pct,
            weakest_themes_count: analyticsOverview.weakest_themes.length,
          });
        } catch (err) {
          logger.warn("[Dashboard] Failed to load analytics overview:", err);
          // Continue with empty data
        }

        try {
          const recentSessionsResponse = await getRecentSessions(10);
          recentSessionsData = recentSessionsResponse.sessions;
          logger.log("[Dashboard] Loaded recent sessions:", recentSessionsData.length);
        } catch (err) {
          logger.warn("[Dashboard] Failed to load recent sessions:", err);
          // Continue with empty data
        }

        // Map recent sessions to dashboard format
        const recentSessions: RecentSession[] = recentSessionsData.map((s, index) => ({
          id: index + 1, // Use index-based ID for display (frontend expects number)
          title: s.title,
          status: s.status,
          score: s.score_correct ?? undefined,
          scorePercentage: s.score_pct ? Math.round(s.score_pct) : undefined,
          href:
            s.status === "in_progress"
              ? `/student/session/${s.session_id}`
              : `/student/session/${s.session_id}/review`,
          blockId: s.block_id ?? undefined,
          themeId: s.theme_id ?? undefined,
        }));

        const unfinishedSession = recentSessions.find((s) => s.status === "in_progress");

        // Determine next action
        const nextAction = determineNextAction(profile, unfinishedSession, blocks, themesByBlock);

        // Calculate streak days and minutes this week from recent sessions
        const now = new Date();
        const startOfWeek = new Date(now);
        startOfWeek.setDate(now.getDate() - now.getDay()); // Sunday
        startOfWeek.setHours(0, 0, 0, 0);
        
        // Calculate streak days (consecutive days with completed sessions)
        let streakDays = 0;
        const completedSessions = recentSessionsData.filter(
          (s) => s.status === "completed" && s.submitted_at
        );
        if (completedSessions.length > 0) {
          const sessionDates = new Set(
            completedSessions
              .map((s) => {
                const date = s.submitted_at ? new Date(s.submitted_at) : null;
                return date ? date.toDateString() : null;
              })
              .filter((d): d is string => d !== null)
          );
          
          // Count consecutive days from today backwards
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          let currentDate = new Date(today);
          
          while (sessionDates.has(currentDate.toDateString())) {
            streakDays++;
            currentDate.setDate(currentDate.getDate() - 1);
          }
        }
        
        // Calculate minutes this week from session durations
        let minutesThisWeek = 0;
        const thisWeekSessions = recentSessionsData.filter((s) => {
          if (!s.started_at) return false;
          const started = new Date(s.started_at);
          return started >= startOfWeek;
        });
        
        for (const session of thisWeekSessions) {
          if (session.started_at && session.submitted_at) {
            const started = new Date(session.started_at);
            const submitted = new Date(session.submitted_at);
            const durationMs = submitted.getTime() - started.getTime();
            const durationMinutes = Math.round(durationMs / (1000 * 60));
            minutesThisWeek += durationMinutes;
          } else if (session.started_at) {
            // For in-progress sessions, estimate based on time since start (capped at 2 hours)
            const started = new Date(session.started_at);
            const durationMs = now.getTime() - started.getTime();
            const durationMinutes = Math.min(Math.round(durationMs / (1000 * 60)), 120);
            minutesThisWeek += durationMinutes;
          }
        }
        
        // Map metrics from analytics
        const metrics: DashboardMetrics = analyticsOverview
          ? {
              streakDays,
              minutesThisWeek,
              questionsThisWeek: analyticsOverview.questions_answered || 0,
            }
          : {
              streakDays,
              minutesThisWeek,
              questionsThisWeek: 0,
            };

        // Map weak themes from analytics
        const weakThemes: WeakTheme[] = analyticsOverview
          ? analyticsOverview.weakest_themes.map((theme) => {
              // Find block for this theme
              const block = blocks.find((b) => {
                // Try to find block by checking if any theme in this block matches
                const blockThemes = themesByBlock[b.id] || [];
                return blockThemes.some((t) => t.id === theme.theme_id);
              });

              return {
                themeId: theme.theme_id,
                themeTitle: theme.theme_name,
                blockId: block?.id || 0,
                blockCode: block?.code || "",
                reason: theme.accuracy_pct < 50 ? "low_accuracy" : "needs_attention",
              };
            })
          : getEmptyWeakThemes();

        // Announcements (not yet implemented in backend)
        const announcements = getEmptyAnnouncements();

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
        logger.error("[Dashboard] Error loading dashboard:", error);
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
  themesByBlock: Record<number, Theme[]>,
): NextAction {
  logger.log("[Dashboard] determineNextAction called with:", {
    profile_exists: !!profile,
    onboarding_completed: profile?.onboarding_completed,
    has_unfinished_session: !!unfinishedSession,
    blocks_count: blocks.length,
  });

  // If onboarding not completed
  if (!profile?.onboarding_completed) {
    logger.log("[Dashboard] Onboarding not completed, showing onboarding prompt");
    return {
      type: "onboarding",
      label: "Complete Onboarding",
      href: "/onboarding",
      hint: "Select your year and blocks to get started",
    };
  }

  // If there's an unfinished session, prioritize resume
  if (unfinishedSession) {
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
  const firstBlockThemes = firstBlock ? themesByBlock[firstBlock.id] || [] : [];
  const firstTheme = firstBlockThemes.length > 0 ? firstBlockThemes[0] : null;

  return {
    type: "quick_practice",
    label: "Start Quick Practice",
    href: "/student/practice/build?preset=quick",
    hint:
      firstBlock && firstTheme
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
