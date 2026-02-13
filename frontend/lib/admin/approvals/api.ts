/**
 * API client for two-person approval system
 */

import fetcher from "@/lib/fetcher";

export interface ApprovalRequest {
  action_type:
    | "PROFILE_SWITCH_PRIMARY"
    | "PROFILE_SWITCH_FALLBACK"
    | "IRT_ACTIVATE"
    | "ELASTICSEARCH_ENABLE"
    | "NEO4J_ENABLE"
    | "SNOWFLAKE_EXPORT_ENABLE";
  action_payload: Record<string, any>;
  reason: string;
  confirmation_phrase: string;
}

export interface ApprovalResponse {
  request_id: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  requested_action?: {
    reason?: string | null;
    [key: string]: unknown;
  } | null;
  requested_by: {
    id: string;
    email: string | null;
  };
  approved_by: {
    id: string;
    email: string | null;
  } | null;
  action_type: string;
  created_at: string;
  decided_at: string | null;
}

export interface ApprovalListResponse {
  approvals: ApprovalResponse[];
}

export interface ApproveRequest {
  confirmation_phrase: string;
}

/**
 * Request approval for a high-risk action
 */
export async function requestApproval(data: ApprovalRequest): Promise<ApprovalResponse> {
  return fetcher<ApprovalResponse>("/api/admin/approvals/request", {
    method: "POST",
    body: data,
  });
}

/**
 * List pending approvals
 */
export async function listPendingApprovals(): Promise<ApprovalListResponse> {
  return fetcher<ApprovalListResponse>("/api/admin/approvals/pending");
}

/**
 * Approve a pending request
 */
export async function approveRequest(
  requestId: string,
  data: ApproveRequest
): Promise<ApprovalResponse> {
  return fetcher<ApprovalResponse>(`/api/admin/approvals/${requestId}/approve`, {
    method: "POST",
    body: data,
  });
}

/**
 * Reject a pending request
 */
export async function rejectRequest(requestId: string): Promise<ApprovalResponse> {
  return fetcher<ApprovalResponse>(`/api/admin/approvals/${requestId}/reject`, {
    method: "POST",
  });
}
