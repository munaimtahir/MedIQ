import { describe, it, expect, vi, beforeEach } from "vitest";
import * as bookmarksApi from "./bookmarksApi";

// Mock fetcher
vi.mock("../fetcher", () => ({
  default: vi.fn(),
}));

import fetcher from "../fetcher";

describe("bookmarksApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("listBookmarks", () => {
    it("should list bookmarks", async () => {
      const mockBookmarks = [
        {
          id: "b1",
          question_id: "q1",
          created_at: "2024-01-01T00:00:00Z",
          question: { id: "q1", text: "Test question" },
        },
      ];

      (fetcher as any).mockResolvedValueOnce(mockBookmarks);

      const result = await bookmarksApi.listBookmarks(0, 10);

      expect(result).toEqual(mockBookmarks);
      expect(fetcher).toHaveBeenCalledWith(
        "/api/v1/bookmarks?skip=0&limit=10",
        expect.objectContaining({
          method: "GET",
        })
      );
    });
  });

  describe("createBookmark", () => {
    it("should create a bookmark", async () => {
      const mockBookmark = {
        id: "b1",
        question_id: "q1",
        created_at: "2024-01-01T00:00:00Z",
      };

      (fetcher as any).mockResolvedValueOnce(mockBookmark);

      const result = await bookmarksApi.createBookmark({
        question_id: "q1",
        notes: "Important",
      });

      expect(result).toEqual(mockBookmark);
      expect(fetcher).toHaveBeenCalledWith(
        "/api/v1/bookmarks",
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });

  describe("deleteBookmark", () => {
    it("should delete a bookmark", async () => {
      (fetcher as any).mockResolvedValueOnce({ success: true });

      await bookmarksApi.deleteBookmark("b1");

      expect(fetcher).toHaveBeenCalledWith(
        "/api/v1/bookmarks/b1",
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });
  });
});
