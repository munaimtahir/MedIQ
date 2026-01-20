/**
 * Admin Import API Client
 */

import type {
  ImportSchemaCreate,
  ImportSchemaListItem,
  ImportSchemaOut,
  ImportSchemaUpdate,
  ImportJobListItem,
  ImportJobOut,
  ImportJobResultOut,
  ActivateSchemaResponse,
} from "@/lib/types/import";

/**
 * Admin Import API
 */
export const adminImportApi = {
  // ============================================================================
  // Schema Management
  // ============================================================================

  /**
   * List all import schemas
   */
  async listSchemas(): Promise<ImportSchemaListItem[]> {
    const response = await fetch("/api/admin/import/schemas", {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load schemas");
    }

    return response.json();
  },

  /**
   * Get schema by ID
   */
  async getSchema(id: string): Promise<ImportSchemaOut> {
    const response = await fetch(`/api/admin/import/schemas/${id}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load schema");
    }

    return response.json();
  },

  /**
   * Create new schema (version 1)
   */
  async createSchema(data: ImportSchemaCreate): Promise<ImportSchemaOut> {
    const response = await fetch("/api/admin/import/schemas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to create schema");
    }

    return response.json();
  },

  /**
   * Create new version of existing schema
   */
  async createNewVersion(id: string, updates: ImportSchemaUpdate): Promise<ImportSchemaOut> {
    const response = await fetch(`/api/admin/import/schemas/${id}/new-version`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to create new version",
      );
    }

    return response.json();
  },

  /**
   * Activate a schema
   */
  async activateSchema(id: string): Promise<ActivateSchemaResponse> {
    const response = await fetch(`/api/admin/import/schemas/${id}/activate`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to activate schema",
      );
    }

    return response.json();
  },

  /**
   * Download CSV template for schema
   */
  async downloadTemplate(id: string): Promise<Blob> {
    const response = await fetch(`/api/admin/import/schemas/${id}/template`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to download template",
      );
    }

    return response.blob();
  },

  // ============================================================================
  // Import Jobs
  // ============================================================================

  /**
   * Import questions from file
   */
  async importQuestions(
    file: File,
    options: { schemaId?: string; dryRun?: boolean } = {},
  ): Promise<ImportJobResultOut> {
    const formData = new FormData();
    formData.append("file", file);
    if (options.schemaId) {
      formData.append("schema_id", options.schemaId);
    }
    formData.append("dry_run", options.dryRun ? "true" : "false");

    const response = await fetch("/api/admin/import/questions", {
      method: "POST",
      credentials: "include",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to import questions",
      );
    }

    return response.json();
  },

  /**
   * List import jobs
   */
  async listJobs(limit = 50): Promise<ImportJobListItem[]> {
    const response = await fetch(`/api/admin/import/jobs?limit=${limit}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load jobs");
    }

    return response.json();
  },

  /**
   * Get job details
   */
  async getJob(id: string): Promise<ImportJobOut> {
    const response = await fetch(`/api/admin/import/jobs/${id}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to load job");
    }

    return response.json();
  },

  /**
   * Download rejected rows CSV
   */
  async downloadRejectedCsv(jobId: string): Promise<Blob> {
    const response = await fetch(`/api/admin/import/jobs/${jobId}/rejected.csv`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to download rejected rows",
      );
    }

    return response.blob();
  },
};
