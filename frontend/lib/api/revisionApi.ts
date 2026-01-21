/**
 * Revision Queue API Client
 */

import { apiRequest } from "./base";

export interface BlockInfo {
  id: string;
  name: string;
}

export interface ThemeInfo {
  id: string;
  name: string;
}

export interface RevisionQueueItem {
  id: string;
  due_date: string;
  status: string;
  priority_score: number;
  recommended_count: number;
  block: BlockInfo;
  theme: ThemeInfo;
  reason: {
    mastery_score?: number;
    mastery_band?: string;
    days_since_last?: number;
    [key: string]: unknown;
  };
}

export interface RevisionQueueListResponse {
  items: RevisionQueueItem[];
  total: number;
}

export interface RevisionQueueUpdateRequest {
  action: "DONE" | "SNOOZE" | "SKIP";
  snooze_days?: number;
}

/**
 * Get revision queue items
 */
export async function getRevisionQueue(
  scope: "today" | "week" = "today",
  status: "DUE" | "DONE" | "SNOOZED" | "SKIPPED" | "ALL" = "DUE",
): Promise<RevisionQueueListResponse> {
  const params = new URLSearchParams({
    scope,
    status,
  });

  return apiRequest<RevisionQueueListResponse>(`/v1/revision/queue?${params}`);
}

/**
 * Update revision queue item status
 */
export async function updateRevisionQueueItem(
  itemId: string,
  request: RevisionQueueUpdateRequest,
): Promise<RevisionQueueItem> {
  return apiRequest<RevisionQueueItem>(`/v1/revision/queue/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(request),
  });
}
