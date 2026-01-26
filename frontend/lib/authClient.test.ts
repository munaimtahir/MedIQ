import { describe, it, expect, vi, beforeEach } from "vitest";
import { authClient } from "./authClient";

// Mock fetch
global.fetch = vi.fn();

describe("authClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("should successfully login with valid credentials", async () => {
      const mockUser = {
        id: "1",
        name: "Test User",
        email: "test@example.com",
        role: "STUDENT" as const,
        onboarding_completed: true,
        is_active: true,
        email_verified: true,
        created_at: "2024-01-01T00:00:00Z",
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { user: mockUser } }),
      });

      const result = await authClient.login({
        email: "test@example.com",
        password: "password123",
      });

      expect(result.data?.user).toEqual(mockUser);
      expect(result.error).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/auth/login",
        expect.objectContaining({
          method: "POST",
          credentials: "include",
        })
      );
    });

    it("should handle login errors", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({
          error: { code: "UNAUTHORIZED", message: "Invalid credentials" },
        }),
      });

      const result = await authClient.login({
        email: "test@example.com",
        password: "wrong",
      });

      expect(result.error?.code).toBe("UNAUTHORIZED");
      expect(result.error?.message).toBe("Invalid credentials");
      expect(result.data).toBeUndefined();
    });

    it("should handle MFA requirement", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { user: null },
          mfa_required: true,
          mfa_token: "mfa-token-123",
        }),
      });

      const result = await authClient.login({
        email: "test@example.com",
        password: "password123",
      });

      expect(result.mfa_required).toBe(true);
      expect(result.mfa_token).toBe("mfa-token-123");
    });
  });

  describe("signup", () => {
    it("should successfully signup a new user", async () => {
      const mockUser = {
        id: "1",
        name: "New User",
        email: "new@example.com",
        role: "STUDENT" as const,
        onboarding_completed: false,
        is_active: true,
        email_verified: false,
        created_at: "2024-01-01T00:00:00Z",
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { user: mockUser } }),
      });

      const result = await authClient.signup({
        name: "New User",
        email: "new@example.com",
        password: "password123",
      });

      expect(result.data?.user).toEqual(mockUser);
      expect(result.error).toBeUndefined();
    });

    it("should handle duplicate email error", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({
          error: { code: "CONFLICT", message: "Email already exists" },
        }),
      });

      const result = await authClient.signup({
        name: "New User",
        email: "existing@example.com",
        password: "password123",
      });

      expect(result.error?.code).toBe("CONFLICT");
      expect(result.data).toBeUndefined();
    });
  });

  describe("me", () => {
    it("should fetch current user", async () => {
      const mockUser = {
        id: "1",
        name: "Test User",
        email: "test@example.com",
        role: "STUDENT" as const,
        onboarding_completed: true,
        is_active: true,
        email_verified: true,
        created_at: "2024-01-01T00:00:00Z",
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { user: mockUser } }),
      });

      const result = await authClient.me();

      expect(result.data?.user).toEqual(mockUser);
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/auth/me",
        expect.objectContaining({
          method: "GET",
          credentials: "include",
        })
      );
    });

    it("should handle unauthenticated user", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({
          error: { code: "UNAUTHORIZED", message: "Not authenticated" },
        }),
      });

      const result = await authClient.me();

      expect(result.error?.code).toBe("UNAUTHORIZED");
      expect(result.data).toBeUndefined();
    });
  });
});
