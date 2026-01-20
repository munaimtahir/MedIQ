/**
 * Analytics API client for student performance metrics
 */

import type { AnalyticsOverview, BlockAnalytics, ThemeAnalytics } from "@/lib/types/analytics";

const BASE_URL = "/api/v1";

export async function getOverview(): Promise<AnalyticsOverview> {
  const res = await fetch(`${BASE_URL}/analytics/overview`, {
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch analytics overview: ${res.statusText}`);
  }

  return res.json();
}

export async function getBlockAnalytics(blockId: number): Promise<BlockAnalytics> {
  const res = await fetch(`${BASE_URL}/analytics/block/${blockId}`, {
    credentials: "include",
  });

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("Block not found");
    }
    throw new Error(`Failed to fetch block analytics: ${res.statusText}`);
  }

  return res.json();
}

export async function getThemeAnalytics(themeId: number): Promise<ThemeAnalytics> {
  const res = await fetch(`${BASE_URL}/analytics/theme/${themeId}`, {
    credentials: "include",
  });

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("Theme not found");
    }
    throw new Error(`Failed to fetch theme analytics: ${res.statusText}`);
  }

  return res.json();
}
