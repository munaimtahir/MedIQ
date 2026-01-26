import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDashboardData } from "./hooks";

// Mock API modules
vi.mock("@/lib/api", () => ({
  syllabusAPI: {
    getYears: vi.fn(),
    getBlocks: vi.fn(),
  },
  onboardingAPI: {
    getProfile: vi.fn(),
  },
}));

vi.mock("@/lib/api/analyticsApi", () => ({
  getOverview: vi.fn(),
  getRecentSessions: vi.fn(),
}));

import { syllabusAPI, onboardingAPI } from "@/lib/api";
import { getOverview, getRecentSessions } from "@/lib/api/analyticsApi";

describe("useDashboardData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should load dashboard data successfully", async () => {
    const mockYears = [
      { id: 1, name: "Year 1", display_name: "1st Year MBBS", order_no: 1 },
    ];
    const mockBlocks = [
      { id: 1, year_id: 1, title: "Block 1", order_no: 1 },
    ];
    const mockOverview = {
      total_sessions: 10,
      accuracy: 0.85,
      avg_time_per_question: 120,
    };
    const mockRecentSessions = [
      {
        session_id: "s1",
        completed_at: "2024-01-01T00:00:00Z",
        score: 85,
      },
    ];

    (syllabusAPI.getYears as any).mockResolvedValueOnce(mockYears);
    (syllabusAPI.getBlocks as any).mockResolvedValueOnce(mockBlocks);
    (onboardingAPI.getProfile as any).mockResolvedValueOnce(null);
    (getOverview as any).mockResolvedValueOnce(mockOverview);
    (getRecentSessions as any).mockResolvedValueOnce(mockRecentSessions);

    const { result } = renderHook(() => useDashboardData());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeTruthy();
    expect(result.current.error).toBeNull();
  });

  it("should handle errors gracefully", async () => {
    (syllabusAPI.getYears as any).mockRejectedValueOnce(
      new Error("Failed to load")
    );

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeNull();
  });
});
