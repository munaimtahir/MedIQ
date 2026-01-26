import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useNotifications } from "./hooks";

// Mock fetch
global.fetch = vi.fn();

// Mock useToast
vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe("useNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should load notifications successfully", async () => {
    const mockNotifications = {
      items: [
        {
          id: "n1",
          type: "info",
          title: "Test notification",
          message: "Test message",
          read: false,
          created_at: "2024-01-01T00:00:00Z",
        },
      ],
      unread_count: 1,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockNotifications,
    });

    const { result } = renderHook(() => useNotifications());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.items).toEqual(mockNotifications.items);
    expect(result.current.error).toBeNull();
  });

  it("should handle errors gracefully", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
  });

  it("should mark all notifications as read", async () => {
    const mockNotifications = {
      items: [
        {
          id: "n1",
          type: "info",
          title: "Test",
          message: "Test",
          read: false,
          created_at: "2024-01-01T00:00:00Z",
        },
      ],
      unread_count: 1,
    };

    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockNotifications,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await result.current.markAllRead();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/notifications/mark-all-read",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      })
    );
  });
});
