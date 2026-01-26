/**
 * Admin Mocks API client
 */

export interface MockBlueprint {
  id: string;
  title: string;
  year: number;
  total_questions: number;
  duration_minutes: number;
  mode: "EXAM" | "TUTOR";
  status: "DRAFT" | "ACTIVE" | "ARCHIVED";
  config: MockBlueprintConfig;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface MockBlueprintConfig {
  coverage: {
    mode: "counts" | "weights";
    items: Array<
      | { theme_id: string; count: number }
      | { theme_id: string; weight: number }
    >;
  };
  difficulty_mix: {
    easy: number;
    medium: number;
    hard: number;
  };
  cognitive_mix: {
    C1: number;
    C2: number;
    C3: number;
  };
  tag_constraints: {
    must_include: {
      theme_ids?: string[];
      concept_ids?: string[];
      tags?: string[];
    };
    must_exclude: {
      question_ids?: string[];
      tags?: string[];
    };
  };
  source_constraints: {
    allow_sources?: string[];
    deny_sources?: string[];
  };
  anti_repeat_policy: {
    avoid_days: number;
    avoid_last_n: number;
  };
  selection_policy: {
    type: "random_weighted";
    notes?: string | null;
  };
}

export interface MockBlueprintVersion {
  id: string;
  blueprint_id: string;
  version: number;
  config: MockBlueprintConfig;
  created_by: string;
  created_at: string;
  diff_summary: string | null;
}

export interface MockGenerationRun {
  id: string;
  blueprint_id: string;
  status: "queued" | "running" | "done" | "failed";
  seed: number;
  config_version_id: string | null;
  requested_by: string;
  started_at: string | null;
  finished_at: string | null;
  generated_question_count: number;
  warnings: Array<Record<string, unknown>> | null;
  errors: Array<Record<string, unknown>> | null;
  created_at: string;
}

export interface MockInstance {
  id: string;
  blueprint_id: string;
  generation_run_id: string;
  year: number;
  total_questions: number;
  duration_minutes: number;
  seed: number;
  question_ids: string[];
  meta: Record<string, unknown> | null;
  created_at: string;
}

export interface MockBlueprintCreate {
  title: string;
  year: number;
  total_questions: number;
  duration_minutes: number;
  mode: "EXAM" | "TUTOR";
  config: MockBlueprintConfig;
}

export interface MockBlueprintUpdate {
  title?: string;
  total_questions?: number;
  duration_minutes?: number;
  config?: MockBlueprintConfig;
}

export interface MockBlueprintActivateRequest {
  reason: string;
  confirmation_phrase: string;
}

export interface MockBlueprintArchiveRequest {
  reason: string;
  confirmation_phrase: string;
}

export interface MockGenerateRequest {
  seed?: number | null;
  reason: string;
  confirmation_phrase: string;
}

export interface MockGenerateResponse {
  run_id: string;
  mock_instance_id: string;
  seed: number;
  warnings: Array<Record<string, unknown>>;
  generated_question_count: number;
}

export interface ListBlueprintsFilters {
  year?: number;
  status?: "DRAFT" | "ACTIVE" | "ARCHIVED";
}

export interface ListRunsFilters {
  blueprint_id?: string;
  page?: number;
  page_size?: number;
  /** @deprecated use page/page_size */
  limit?: number;
}

export interface ListInstancesFilters {
  blueprint_id?: string;
  page?: number;
  page_size?: number;
  /** @deprecated use page/page_size */
  limit?: number;
}

interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export const adminMocksAPI = {
  /**
   * List blueprints
   */
  listBlueprints: async (filters?: ListBlueprintsFilters): Promise<MockBlueprint[]> => {
    const params = new URLSearchParams();
    if (filters?.year) params.set("year", filters.year.toString());
    if (filters?.status) params.set("status", filters.status);
    // Default to a bounded page_size to avoid large payloads.
    params.set("page", "1");
    params.set("page_size", "100");

    const response = await fetch(`/api/admin/mocks/blueprints?${params.toString()}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load blueprints");
    }

    const data = (await response.json()) as Paginated<MockBlueprint> | MockBlueprint[];
    return Array.isArray(data) ? data : data.items;
  },

  /**
   * Get blueprint by ID
   */
  getBlueprint: async (id: string): Promise<MockBlueprint> => {
    const response = await fetch(`/api/admin/mocks/blueprints/${id}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load blueprint");
    }

    return response.json();
  },

  /**
   * Create blueprint
   */
  createBlueprint: async (payload: MockBlueprintCreate): Promise<MockBlueprint> => {
    const response = await fetch("/api/admin/mocks/blueprints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to create blueprint");
    }

    return response.json();
  },

  /**
   * Update blueprint
   */
  updateBlueprint: async (id: string, payload: MockBlueprintUpdate): Promise<MockBlueprint> => {
    const response = await fetch(`/api/admin/mocks/blueprints/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to update blueprint");
    }

    return response.json();
  },

  /**
   * Activate blueprint
   */
  activateBlueprint: async (
    id: string,
    request: MockBlueprintActivateRequest,
  ): Promise<MockBlueprint> => {
    const response = await fetch(`/api/admin/mocks/blueprints/${id}/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to activate blueprint");
    }

    return response.json();
  },

  /**
   * Archive blueprint
   */
  archiveBlueprint: async (
    id: string,
    request: MockBlueprintArchiveRequest,
  ): Promise<MockBlueprint> => {
    const response = await fetch(`/api/admin/mocks/blueprints/${id}/archive`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to archive blueprint");
    }

    return response.json();
  },

  /**
   * Generate mock instance
   */
  generateMock: async (id: string, request: MockGenerateRequest): Promise<MockGenerateResponse> => {
    const response = await fetch(`/api/admin/mocks/blueprints/${id}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to generate mock");
    }

    return response.json();
  },

  /**
   * List generation runs
   */
  listRuns: async (filters?: ListRunsFilters): Promise<MockGenerationRun[]> => {
    const params = new URLSearchParams();
    if (filters?.blueprint_id) params.set("blueprint_id", filters.blueprint_id);
    if (filters?.page) params.set("page", filters.page.toString());
    if (filters?.page_size) params.set("page_size", filters.page_size.toString());
    if (filters?.limit) params.set("limit", filters.limit.toString()); // legacy

    // Default (bounded)
    if (!params.get("page")) params.set("page", "1");
    if (!params.get("page_size")) params.set("page_size", "50");

    const response = await fetch(`/api/admin/mocks/runs?${params.toString()}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load runs");
    }

    const data = (await response.json()) as Paginated<MockGenerationRun> | MockGenerationRun[];
    return Array.isArray(data) ? data : data.items;
  },

  /**
   * Get run by ID
   */
  getRun: async (runId: string): Promise<MockGenerationRun> => {
    const response = await fetch(`/api/admin/mocks/runs/${runId}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load run");
    }

    return response.json();
  },

  /**
   * List instances
   */
  listInstances: async (filters?: ListInstancesFilters): Promise<MockInstance[]> => {
    const params = new URLSearchParams();
    if (filters?.blueprint_id) params.set("blueprint_id", filters.blueprint_id);
    if (filters?.page) params.set("page", filters.page.toString());
    if (filters?.page_size) params.set("page_size", filters.page_size.toString());
    if (filters?.limit) params.set("limit", filters.limit.toString()); // legacy

    if (!params.get("page")) params.set("page", "1");
    if (!params.get("page_size")) params.set("page_size", "50");

    const response = await fetch(`/api/admin/mocks/instances?${params.toString()}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load instances");
    }

    const data = (await response.json()) as Paginated<MockInstance> | MockInstance[];
    return Array.isArray(data) ? data : data.items;
  },

  /**
   * Get instance by ID
   */
  getInstance: async (instanceId: string): Promise<MockInstance> => {
    const response = await fetch(`/api/admin/mocks/instances/${instanceId}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load instance");
    }

    return response.json();
  },
};
