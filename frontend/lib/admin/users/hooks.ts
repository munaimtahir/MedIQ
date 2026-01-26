/**
 * Hooks for admin user management.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { adminUsersAPI } from "./api";
import { User, UserCreate, UserUpdate, UsersListResponse } from "./types";
import { notify } from "@/lib/notify";
import { useUserStore, selectUser } from "@/store/userStore";

interface UseAdminUsersParams {
  q?: string;
  role?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

interface UseAdminUsersResult {
  users: User[];
  loading: boolean;
  error: Error | null;
  page: number;
  pageSize: number;
  total: number;
  refetch: () => void;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setSearch: (q: string) => void;
  setRoleFilter: (role: string | undefined) => void;
  setStatusFilter: (status: string | undefined) => void;
}

/**
 * Hook for fetching and managing users list.
 */
export function useAdminUsers(params: UseAdminUsersParams = {}): UseAdminUsersResult {
  const [state, setState] = useState<{
    users: User[];
    loading: boolean;
    error: Error | null;
    page: number;
    pageSize: number;
    total: number;
    search: string;
    roleFilter: string | undefined;
    statusFilter: string | undefined;
  }>({
    users: [],
    loading: true,
    error: null,
    page: params.page || 1,
    pageSize: params.page_size || 20,
    total: 0,
    search: params.q || "",
    roleFilter: params.role,
    statusFilter: params.status,
  });

  const stateRef = useRef(state);
  stateRef.current = state;

  const loadUsers = useCallback(async () => {
    const currentState = stateRef.current;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const data: UsersListResponse = await adminUsersAPI.listUsers({
        q: currentState.search || undefined,
        role: currentState.roleFilter,
        status: currentState.statusFilter,
        page: currentState.page,
        page_size: currentState.pageSize,
      });
      setState((prev) => ({
        ...prev,
        users: data.items,
        total: data.total,
        loading: false,
      }));
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load users");
      setState((prev) => ({
        ...prev,
        loading: false,
        error,
      }));
      notify.error("Failed to load users", error.message);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Reload when filters change
  useEffect(() => {
    loadUsers();
  }, [state.search, state.roleFilter, state.statusFilter, state.page, state.pageSize, loadUsers]);

  return {
    users: state.users,
    loading: state.loading,
    error: state.error,
    page: state.page,
    pageSize: state.pageSize,
    total: state.total,
    refetch: loadUsers,
    setPage: (page: number) => setState((prev) => ({ ...prev, page })),
    setPageSize: (size: number) => setState((prev) => ({ ...prev, pageSize: size, page: 1 })),
    setSearch: (q: string) => setState((prev) => ({ ...prev, search: q, page: 1 })),
    setRoleFilter: (role: string | undefined) =>
      setState((prev) => ({ ...prev, roleFilter: role, page: 1 })),
    setStatusFilter: (status: string | undefined) =>
      setState((prev) => ({ ...prev, statusFilter: status, page: 1 })),
  };
}

/**
 * Hook for user mutations.
 */
export function useUserMutations() {
  const createUser = useCallback(async (data: UserCreate) => {
    try {
      const user = await adminUsersAPI.createUser(data);
      notify.success("User created", `User "${user.name}" created successfully`);
      return user;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to create user");
      notify.error("Failed to create user", error.message);
      throw error;
    }
  }, []);

  const updateUser = useCallback(async (id: string, data: UserUpdate) => {
    try {
      const user = await adminUsersAPI.updateUser(id, data);
      notify.success("User updated", `User "${user.name}" updated successfully`);
      return user;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update user");
      notify.error("Failed to update user", error.message);
      throw error;
    }
  }, []);

  const enableUser = useCallback(async (id: string) => {
    try {
      const user = await adminUsersAPI.enableUser(id);
      notify.success("User enabled", `User "${user.name}" enabled successfully`);
      return user;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to enable user");
      notify.error("Failed to enable user", error.message);
      throw error;
    }
  }, []);

  const disableUser = useCallback(async (id: string) => {
    try {
      const user = await adminUsersAPI.disableUser(id);
      notify.success("User disabled", `User "${user.name}" disabled successfully`);
      return user;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to disable user");
      notify.error("Failed to disable user", error.message);
      throw error;
    }
  }, []);

  const triggerPasswordReset = useCallback(async (id: string) => {
    try {
      const result = await adminUsersAPI.triggerPasswordReset(id);
      if (result.email_sent) {
        notify.success("Password reset sent", "Password reset email sent successfully");
      } else {
        notify.success("Password reset token generated", result.message);
      }
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to trigger password reset");
      notify.error("Failed to trigger password reset", error.message);
      throw error;
    }
  }, []);

  return {
    createUser,
    updateUser,
    enableUser,
    disableUser,
    triggerPasswordReset,
  };
}

/**
 * Hook to get current user ID for guardrails.
 */
export function useCurrentUserId(): string | null {
  const user = useUserStore(selectUser);
  return user?.id || null;
}
