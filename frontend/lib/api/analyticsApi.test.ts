import { describe, it, expect, vi, beforeEach } from "vitest";
import * as analyticsApi from "./analyticsApi";

// Mock fetch
global.fetch = vi.fn();

describe("analyticsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getOverview", () => {
    it("should fetch analytics overview", async () => {
      const mockOverview = {
        total_sessions: 10,
        total_questions_answered: 100,
        accuracy: 0.85,
        avg_time_per_question: 120,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockOverview,
      });

      const result = await analyticsApi.getOverview();

      expect(result).toEqual(mockOverview);
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/v1/analytics/overview",
        expect.objectContaining({
          credentials: "include",
        })
      );
    });

    it("should handle errors", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });

      await expect(analyticsApi.getOverview()).rejects.toThrow(
        "Failed to fetch analytics overview"
      );
    });
  });

  describe("getBlockAnalytics", () => {
    it("should fetch block analytics", async () => {
      const mockBlockAnalytics = {
        block_id: 1,
        total_sessions: 5,
        accuracy: 0.8,
        themes: [],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockBlockAnalytics,
      });

      const result = await analyticsApi.getBlockAnalytics(1);

      expect(result).toEqual(mockBlockAnalytics);
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/v1/analytics/block/1",
        expect.objectContaining({
          credentials: "include",
        })
      );
    });

    it("should handle 404 for non-existent block", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
      });

      await expect(analyticsApi.getBlockAnalytics(999)).rejects.toThrow("Block not found");
    });
  });

  describe("getThemeAnalytics", () => {
    it("should fetch theme analytics", async () => {
      const mockThemeAnalytics = {
        theme_id: 1,
        total_sessions: 3,
        accuracy: 0.75,
        questions: [],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockThemeAnalytics,
      });

      const result = await analyticsApi.getThemeAnalytics(1);

      expect(result).toEqual(mockThemeAnalytics);
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/v1/analytics/theme/1",
        expect.objectContaining({
          credentials: "include",
        })
      );
    });
  });

  describe("getRecentSessions", () => {
    it("should fetch recent sessions", async () => {
      const mockSessions = [
        {
          session_id: "s1",
          completed_at: "2024-01-01T00:00:00Z",
          score: 85,
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessions,
      });

      const result = await analyticsApi.getRecentSessions();

      expect(result).toEqual(mockSessions);
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/v1/analytics/recent-sessions",
        expect.objectContaining({
          credentials: "include",
        })
      );
    });
  });
});
