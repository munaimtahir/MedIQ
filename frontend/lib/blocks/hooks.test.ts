import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useBlocks } from "./hooks";

// Mock API
vi.mock("@/lib/api", () => ({
  syllabusAPI: {
    getBlocks: vi.fn(),
    getThemes: vi.fn(),
  },
}));

import { syllabusAPI } from "@/lib/api";

describe("useBlocks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should load blocks successfully", async () => {
    const mockBlocks = [
      { id: 1, year_id: 1, title: "Block 1", order_no: 1 },
      { id: 2, year_id: 1, title: "Block 2", order_no: 2 },
    ];

    (syllabusAPI.getBlocks as any).mockResolvedValueOnce(mockBlocks);

    const { result } = renderHook(() => useBlocks(1));

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.blocks).toEqual(mockBlocks);
    expect(result.current.error).toBeNull();
  });

  it("should handle errors", async () => {
    (syllabusAPI.getBlocks as any).mockRejectedValueOnce(
      new Error("Failed to load")
    );

    const { result } = renderHook(() => useBlocks(1));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
  });
});
