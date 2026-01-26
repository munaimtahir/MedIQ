/**
 * SWR hooks for data fetching with automatic caching and revalidation
 */

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

/**
 * Fetch blocks for a year with SWR caching
 */
export function useBlocks(yearName: string | null) {
  return useSWR(
    yearName ? `/api/syllabus/years/${yearName}/blocks` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 60000, // 1 minute
    }
  );
}

/**
 * Fetch themes for a block with SWR caching
 */
export function useThemes(blockId: number | null) {
  return useSWR(
    blockId ? `/api/syllabus/blocks/${blockId}/themes` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 60000, // 1 minute
    }
  );
}

/**
 * Fetch notifications with SWR caching
 */
export function useNotificationsSWR() {
  return useSWR("/api/notifications", fetcher, {
    refreshInterval: 30000, // Refresh every 30 seconds
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
  });
}

/**
 * Fetch user profile with SWR caching
 */
export function useUserProfile() {
  return useSWR("/api/users/me/profile", fetcher, {
    revalidateOnFocus: false,
    revalidateOnReconnect: true,
    dedupingInterval: 300000, // 5 minutes
  });
}
