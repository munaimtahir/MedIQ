/**
 * Dashboard view model types.
 */

import { Block, Theme, Year } from "@/lib/api";

export interface DashboardVM {
  user: {
    name?: string;
    yearName?: string;
    yearId?: number;
  };
  blocks: Block[];
  themesByBlock: Record<number, Theme[]>;
  nextAction: NextAction;
  metrics: DashboardMetrics;
  weakThemes: WeakTheme[];
  recentSessions: RecentSession[];
  announcements: Announcement[];
  hasUnfinishedSession: boolean;
  unfinishedSession?: RecentSession;
}

export interface NextAction {
  type: "resume" | "quick_practice" | "build" | "onboarding";
  label: string;
  href: string;
  hint?: string;
  secondaryActions?: Array<{
    label: string;
    href: string;
  }>;
}

export interface DashboardMetrics {
  streakDays: number;
  minutesThisWeek: number;
  questionsThisWeek: number;
}

export interface WeakTheme {
  themeId: number;
  themeTitle: string;
  blockId: number;
  blockCode: string;
  reason: "low_accuracy" | "needs_attention" | "not_practiced";
}

export interface RecentSession {
  id: number;
  title: string;
  status: "completed" | "in_progress" | "abandoned";
  score?: number;
  scorePercentage?: number;
  href: string;
  blockId?: number;
  themeId?: number;
}

export interface Announcement {
  id: number;
  title: string;
  date: string;
  body?: string;
}
