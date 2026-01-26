/**
 * SWR hooks for notifications
 */

import useSWR, { mutate } from "swr";
import useSWRMutation from "swr/mutation";
import fetcher from "@/lib/fetcher";

const API_BASE = "/api/v1";

/**
 * Hook to fetch notifications list with pagination
 */
export function useNotifications(params: {
  unread_only?: boolean;
  page?: number;
  page_size?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params.unread_only !== undefined) {
    searchParams.append("unread_only", String(params.unread_only));
  }
  if (params.page !== undefined) {
    searchParams.append("page", String(params.page));
  }
  if (params.page_size !== undefined) {
    searchParams.append("page_size", String(params.page_size));
  }

  const key = `${API_BASE}/notifications?${searchParams.toString()}`;

  return useSWR(key, fetcher, {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
    dedupingInterval: 30000, // 30 seconds
  });
}

/**
 * Hook to fetch unread count
 */
export function useUnreadCount() {
  return useSWR(`${API_BASE}/notifications/unread-count`, fetcher, {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
    refreshInterval: 30000, // Refetch every 30 seconds
    dedupingInterval: 30000,
  });
}

/**
 * Hook to mark a notification as read
 */
export function useMarkRead() {
  return useSWRMutation(
    (id: string) => `${API_BASE}/notifications/${id}/read`,
    async (url: string) => {
      const response = await fetch(url, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("Failed to mark as read");
      }
      return response.json();
    },
    {
      onSuccess: () => {
        // Invalidate notifications list and unread count
        void mutate((key) => typeof key === "string" && key.startsWith(`${API_BASE}/notifications`));
      },
    },
  );
}

/**
 * Hook to mark all notifications as read
 */
export function useMarkAllRead() {
  return useSWRMutation(
    () => `${API_BASE}/notifications/read-all`,
    async (url: string) => {
      const response = await fetch(url, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("Failed to mark all as read");
      }
      return response.json();
    },
    {
      onSuccess: () => {
        // Invalidate notifications list and unread count
        void mutate((key) => typeof key === "string" && key.startsWith(`${API_BASE}/notifications`));
      },
    },
  );
}
