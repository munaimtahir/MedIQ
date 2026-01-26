/**
 * Admin Audit Log API Client
 */

import type { AuditLogItem, AuditLogQuery } from "@/lib/types/question-cms";

/**
 * Build query string from AuditLogQuery
 */
function buildQueryString(params: AuditLogQuery): string {
  const searchParams = new URLSearchParams();

  if (params.entity_type) searchParams.set("entity_type", params.entity_type);
  if (params.entity_id) searchParams.set("entity_id", params.entity_id);
  if (params.action) searchParams.set("action", params.action);
  if (params.actor_id) searchParams.set("actor_id", params.actor_id);
  if (params.from) searchParams.set("from", params.from);
  if (params.to) searchParams.set("to", params.to);
  if (params.page) searchParams.set("page", params.page.toString());
  if (params.page_size) searchParams.set("page_size", params.page_size.toString());

  return searchParams.toString();
}

/**
 * Admin Audit API
 */
export const adminAuditApi = {
  /**
   * Query audit log
   */
  async queryAuditLog(params: AuditLogQuery = {}): Promise<AuditLogItem[]> {
    const queryString = buildQueryString(params);
    const url = `/api/admin/audit${queryString ? `?${queryString}` : ""}`;

    const response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load audit log");
    }

    const data = (await response.json()) as
      | { items: AuditLogItem[]; page: number; page_size: number; total: number }
      | AuditLogItem[];
    return Array.isArray(data) ? data : data.items;
  },
};
