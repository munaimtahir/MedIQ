/**
 * Admin email API client
 */

import fetcher from "../fetcher";

const API_BASE = "/api/v1";

export interface EmailRuntimeResponse {
  requested_mode: string;
  effective_mode: string;
  freeze: boolean;
  provider: {
    type: string;
    configured: boolean;
  };
  warnings: string[];
  blocking_reasons: string[];
}

export interface EmailModeSwitchRequest {
  mode: string;
  reason: string;
  confirmation_phrase: string;
}

export interface EmailOutboxItem {
  id: string;
  to_email: string;
  to_name: string | null;
  subject: string;
  template_key: string;
  status: string;
  provider: string | null;
  provider_message_id: string | null;
  attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  sent_at: string | null;
}

export interface EmailOutboxDetail extends EmailOutboxItem {
  body_text?: string | null;
  body_html?: string | null;
  template_vars?: Record<string, unknown>;
}

export interface EmailOutboxListResponse {
  items: EmailOutboxItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface DrainOutboxRequest {
  limit?: number;
  reason: string;
  confirmation_phrase: string;
}

export interface DrainOutboxResponse {
  attempted: number;
  sent: number;
  failed: number;
  skipped: number;
  effective_mode: string;
}

export const adminEmailApi = {
  /**
   * Get email runtime configuration
   */
  async getRuntime(): Promise<EmailRuntimeResponse> {
    return fetcher<EmailRuntimeResponse>(`${API_BASE}/admin/email/runtime`, {
      method: "GET",
    });
  },

  /**
   * Switch email mode
   */
  async switchMode(
    mode: string,
    reason: string,
    confirmationPhrase: string,
  ): Promise<EmailRuntimeResponse> {
    return fetcher<EmailRuntimeResponse>(`${API_BASE}/admin/email/runtime/switch`, {
      method: "POST",
      body: { mode, reason, confirmation_phrase: confirmationPhrase },
    });
  },

  /**
   * List email outbox items
   */
  async listOutbox(params: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<EmailOutboxListResponse> {
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.append("status", params.status);
    if (params.page) searchParams.append("page", String(params.page));
    if (params.page_size) searchParams.append("page_size", String(params.page_size));

    const query = searchParams.toString();
    return fetcher<EmailOutboxListResponse>(
      `${API_BASE}/admin/email/outbox${query ? `?${query}` : ""}`,
      {
        method: "GET",
      },
    );
  },

  /**
   * Get email outbox item by ID
   */
  async getOutboxItem(id: string): Promise<EmailOutboxDetail> {
    return fetcher<EmailOutboxDetail>(`${API_BASE}/admin/email/outbox/${id}`, {
      method: "GET",
    });
  },

  /**
   * Drain email outbox
   */
  async drainOutbox(data: {
    limit: number;
    reason: string;
    phrase: string;
  }): Promise<DrainOutboxResponse> {
    return fetcher<DrainOutboxResponse>(`${API_BASE}/admin/email/outbox/drain`, {
      method: "POST",
      body: {
        limit: data.limit,
        reason: data.reason,
        confirmation_phrase: data.phrase,
      },
    });
  },
};
