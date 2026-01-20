/**
 * Admin Questions CMS API Client
 */

import type {
  QuestionListItem,
  QuestionOut,
  QuestionCreate,
  QuestionUpdate,
  QuestionListQuery,
  WorkflowActionOut,
  RejectRequest,
  VersionOut,
} from "@/lib/types/question-cms";

/**
 * Build query string from QuestionListQuery
 */
function buildQueryString(params: QuestionListQuery): string {
  const searchParams = new URLSearchParams();

  if (params.status) searchParams.set("status", params.status);
  if (params.year_id) searchParams.set("year_id", params.year_id.toString());
  if (params.block_id) searchParams.set("block_id", params.block_id.toString());
  if (params.theme_id) searchParams.set("theme_id", params.theme_id.toString());
  if (params.difficulty) searchParams.set("difficulty", params.difficulty);
  if (params.cognitive_level) searchParams.set("cognitive_level", params.cognitive_level);
  if (params.source_book) searchParams.set("source_book", params.source_book);
  if (params.q) searchParams.set("q", params.q);
  if (params.page) searchParams.set("page", params.page.toString());
  if (params.page_size) searchParams.set("page_size", params.page_size.toString());
  if (params.sort) searchParams.set("sort", params.sort);
  if (params.order) searchParams.set("order", params.order);

  return searchParams.toString();
}

/**
 * Admin Questions API
 */
export const adminQuestionsApi = {
  /**
   * List questions with filters
   */
  async listQuestions(params: QuestionListQuery = {}): Promise<QuestionListItem[]> {
    const queryString = buildQueryString(params);
    const url = `/api/admin/questions${queryString ? `?${queryString}` : ""}`;

    const response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load questions");
    }

    return response.json();
  },

  /**
   * Get single question by ID
   */
  async getQuestion(id: string): Promise<QuestionOut> {
    const response = await fetch(`/api/admin/questions/${id}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load question");
    }

    return response.json();
  },

  /**
   * Create new question (starts as DRAFT)
   */
  async createQuestion(data: QuestionCreate): Promise<QuestionOut> {
    const response = await fetch("/api/admin/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to create question");
    }

    return response.json();
  },

  /**
   * Update question
   */
  async updateQuestion(id: string, data: QuestionUpdate): Promise<QuestionOut> {
    const response = await fetch(`/api/admin/questions/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to update question");
    }

    return response.json();
  },

  /**
   * Delete question (hard delete, ADMIN only)
   */
  async deleteQuestion(id: string): Promise<void> {
    const response = await fetch(`/api/admin/questions/${id}`, {
      method: "DELETE",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to delete question");
    }
  },

  // ============================================================================
  // Workflow Actions
  // ============================================================================

  /**
   * Submit question for review (DRAFT -> IN_REVIEW)
   */
  async submitQuestion(id: string): Promise<WorkflowActionOut> {
    const response = await fetch(`/api/admin/questions/${id}/submit`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to submit question");
    }

    return response.json();
  },

  /**
   * Approve question (IN_REVIEW -> APPROVED)
   */
  async approveQuestion(id: string): Promise<WorkflowActionOut> {
    const response = await fetch(`/api/admin/questions/${id}/approve`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to approve question",
      );
    }

    return response.json();
  },

  /**
   * Reject question (IN_REVIEW -> DRAFT)
   */
  async rejectQuestion(id: string, reason: string): Promise<WorkflowActionOut> {
    const rejectData: RejectRequest = { reason };
    const response = await fetch(`/api/admin/questions/${id}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(rejectData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to reject question");
    }

    return response.json();
  },

  /**
   * Publish question (APPROVED -> PUBLISHED, ADMIN only)
   */
  async publishQuestion(id: string): Promise<WorkflowActionOut> {
    const response = await fetch(`/api/admin/questions/${id}/publish`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to publish question",
      );
    }

    return response.json();
  },

  /**
   * Unpublish question (PUBLISHED -> APPROVED, ADMIN only)
   */
  async unpublishQuestion(id: string): Promise<WorkflowActionOut> {
    const response = await fetch(`/api/admin/questions/${id}/unpublish`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to unpublish question",
      );
    }

    return response.json();
  },

  // ============================================================================
  // Version History
  // ============================================================================

  /**
   * Get version history for question
   */
  async listVersions(questionId: string): Promise<VersionOut[]> {
    const response = await fetch(`/api/admin/questions/${questionId}/versions`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to load version history",
      );
    }

    return response.json();
  },

  /**
   * Get specific version
   */
  async getVersion(questionId: string, versionId: string): Promise<VersionOut> {
    const response = await fetch(`/api/admin/questions/${questionId}/versions/${versionId}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load version");
    }

    return response.json();
  },
};
