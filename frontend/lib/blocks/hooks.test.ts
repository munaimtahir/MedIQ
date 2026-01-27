import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useThemes } from "./hooks";

// Mock API
vi.mock("@/lib/api", () => ({
  syllabusAPI: {
    getBlocks: vi.fn(),
    getThemes: vi.fn(),
  },
}));

import { syllabusAPI } from "@/lib/api";

describe("useThemes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should load themes successfully", async () => {
    const mockThemes = [
      { id: 1, block_id: 1, title: "Theme 1", order_no: 1 },
      { id: 2, block_id: 1, title: "Theme 2", order_no: 2 },
    ];

    (syllabusAPI.getThemes as any).mockResolvedValueOnce(mockThemes);

    const { result } = renderHook(() => useThemes(1));

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.themes).toEqual(mockThemes);
    expect(result.current.error).toBeNull();
  });

  it("should handle errors", async () => {
    (syllabusAPI.getThemes as any).mockRejectedValueOnce(
      new Error("Failed to load")
    );

    const { result } = renderHook(() => useThemes(1));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
  });
});
