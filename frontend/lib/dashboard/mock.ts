/**
 * Mock data generators for dashboard features not yet implemented in backend.
 */

import { DashboardMetrics, WeakTheme, RecentSession, Announcement } from "./types";

export function getMockMetrics(): DashboardMetrics {
  return {
    streakDays: 7,
    minutesThisWeek: 180,
    questionsThisWeek: 45,
  };
}

export function getMockWeakThemes(): WeakTheme[] {
  return [
    {
      themeId: 1,
      themeTitle: "Anemias",
      blockId: 1,
      blockCode: "A",
      reason: "low_accuracy",
    },
    {
      themeId: 2,
      themeTitle: "Cardiovascular System",
      blockId: 1,
      blockCode: "A",
      reason: "needs_attention",
    },
    {
      themeId: 3,
      themeTitle: "Respiratory System",
      blockId: 1,
      blockCode: "B",
      reason: "not_practiced",
    },
  ];
}

export function getMockRecentSessions(): RecentSession[] {
  return [
    {
      id: 1,
      title: "Block A → Anemias",
      status: "completed",
      score: 8,
      scorePercentage: 80,
      href: "/student/session/1/review",
      blockId: 1,
      themeId: 1,
    },
    {
      id: 2,
      title: "Block B → Respiratory System",
      status: "in_progress",
      href: "/student/session/2",
      blockId: 1,
      themeId: 3,
    },
    {
      id: 3,
      title: "Block A → Cardiovascular",
      status: "completed",
      score: 6,
      scorePercentage: 60,
      href: "/student/session/3/review",
      blockId: 1,
      themeId: 2,
    },
  ];
}

export function getMockAnnouncements(): Announcement[] {
  return [
    {
      id: 1,
      title: "New themes added to Block B",
      date: "2024-01-15",
      body: "We've added 5 new themes covering advanced respiratory topics.",
    },
  ];
}

export function getEmptyMetrics(): DashboardMetrics {
  return {
    streakDays: 0,
    minutesThisWeek: 0,
    questionsThisWeek: 0,
  };
}

export function getEmptyWeakThemes(): WeakTheme[] {
  return [];
}

export function getEmptyRecentSessions(): RecentSession[] {
  return [];
}

export function getEmptyAnnouncements(): Announcement[] {
  return [];
}
