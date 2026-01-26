/**
 * Hooks for notifications data fetching.
 */

import { useEffect, useState } from "react";
import { NotificationItem, NotificationsResponse, MarkAllReadResponse } from "./types";
import { useToast } from "@/components/ui/use-toast";
import { logger } from "@/lib/logger";

interface UseNotificationsResult {
  items: NotificationItem[];
  loading: boolean;
  error: Error | null;
  refetch: () => void;
  markAllRead: () => Promise<void>;
  markAllReadSupported: boolean;
}

/**
 * Fetch notifications with fallback to mock data in dev mode.
 */
export function useNotifications(): UseNotificationsResult {
  const { toast } = useToast();
  const [state, setState] = useState<UseNotificationsResult>({
    items: [],
    loading: true,
    error: null,
    refetch: () => {},
    markAllRead: async () => {},
    markAllReadSupported: true,
  });

  const loadNotifications = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await fetch("/api/notifications", {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to load notifications");
      }

      const data: NotificationsResponse = await response.json();
      setState((prev) => ({
        ...prev,
        items: data.items || [],
        loading: false,
        error: null,
        refetch: loadNotifications,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error : new Error("Failed to load notifications"),
        refetch: loadNotifications,
      }));
    }
  };

  const markAllRead = async () => {
    try {
      const response = await fetch("/api/notifications/mark-all-read", {
        method: "POST",
        credentials: "include",
      });

      if (response.status === 501) {
        // Not implemented
        setState((prev) => ({ ...prev, markAllReadSupported: false }));
        toast({
          title: "Coming soon",
          description: "Mark all as read is not yet available",
        });
        return;
      }

      if (!response.ok) {
        throw new Error("Failed to mark all as read");
      }

      const data: MarkAllReadResponse = await response.json();

      // Update local state - mark all items as read
      setState((prev) => {
        const updatedCount = data.updated || prev.items.length;
        toast({
          title: "Marked as read",
          description: `${updatedCount} notification(s) marked as read`,
        });
        return {
          ...prev,
          items: prev.items.map((item) => ({
            ...item,
            read_at: item.read_at || new Date().toISOString(),
          })),
        };
      });
    } catch (error) {
      logger.error("Failed to mark all as read:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to mark all as read",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  // Return state with current markAllRead function
  return {
    ...state,
    markAllRead,
  };
}
