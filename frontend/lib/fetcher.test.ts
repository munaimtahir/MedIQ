import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetcher, type FetcherError } from "./fetcher";

// Mock fetch
global.fetch = vi.fn();

describe("fetcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should return data on successful response", async () => {
    const mockData = { id: 1, name: "Test" };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const result = await fetcher("/api/test");
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith("/api/test", expect.objectContaining({
      method: "GET",
      credentials: "include",
    }));
  });

  it("should normalize errors to {status, code, message} shape", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Not found" }),
    });

    try {
      await fetcher("/api/test");
      expect.fail("Should have thrown");
    } catch (error) {
      const err = error as FetcherError;
      expect(err.status).toBe(404);
      expect(err.code).toBe("NOT_FOUND");
      expect(err.message).toBe("Not found");
    }
  });

  it("should handle error with {error: {code, message}} shape", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: { code: "VALIDATION_ERROR", message: "Invalid input" } }),
    });

    try {
      await fetcher("/api/test");
      expect.fail("Should have thrown");
    } catch (error) {
      const err = error as FetcherError;
      expect(err.status).toBe(400);
      expect(err.code).toBe("VALIDATION_ERROR");
      expect(err.message).toBe("Invalid input");
    }
  });

  it("should handle POST requests with body", async () => {
    const mockData = { success: true };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const body = { name: "Test" };
    await fetcher("/api/test", { method: "POST", body });

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/test",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(body),
      })
    );
  });
});
