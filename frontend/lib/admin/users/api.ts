/**
 * API client for admin user management.
 */

import { User, UserCreate, UserUpdate, UsersListResponse, PasswordResetResponse } from "./types";

export const adminUsersAPI = {
  /**
   * List users with pagination and filters.
   */
  listUsers: async (params: {
    q?: string;
    role?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<UsersListResponse> => {
    const searchParams = new URLSearchParams();
    if (params.q) searchParams.set("q", params.q);
    if (params.role) searchParams.set("role", params.role);
    if (params.status) searchParams.set("status", params.status);
    if (params.page) searchParams.set("page", params.page.toString());
    if (params.page_size) searchParams.set("page_size", params.page_size.toString());

    const queryString = searchParams.toString() ? `?${searchParams.toString()}` : "";

    const response = await fetch(`/api/admin/users${queryString}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load users");
    }

    return response.json();
  },

  /**
   * Create a new user.
   */
  createUser: async (data: UserCreate): Promise<User> => {
    const response = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to create user");
    }

    return response.json();
  },

  /**
   * Update a user.
   */
  updateUser: async (id: string, data: UserUpdate): Promise<User> => {
    const response = await fetch(`/api/admin/users/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to update user");
    }

    return response.json();
  },

  /**
   * Enable a user.
   */
  enableUser: async (id: string): Promise<User> => {
    const response = await fetch(`/api/admin/users/${id}/enable`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to enable user");
    }

    return response.json();
  },

  /**
   * Disable a user.
   */
  disableUser: async (id: string): Promise<User> => {
    const response = await fetch(`/api/admin/users/${id}/disable`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to disable user");
    }

    return response.json();
  },

  /**
   * Trigger password reset for a user.
   */
  triggerPasswordReset: async (id: string): Promise<PasswordResetResponse> => {
    const response = await fetch(`/api/admin/users/${id}/password-reset`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to trigger password reset");
    }

    return response.json();
  },
};
