// ============================================================================
// Onboarding Types
// ============================================================================

export interface OnboardingBlockOption {
  id: number;
  code: string;
  display_name: string;
}

export interface OnboardingSubjectOption {
  id: number;
  code: string | null;
  display_name: string;
}

export interface OnboardingYearOption {
  id: number;
  slug: string;
  display_name: string;
  blocks: OnboardingBlockOption[];
  subjects: OnboardingSubjectOption[];
}

export interface OnboardingOptions {
  years: OnboardingYearOption[];
}

export interface OnboardingRequest {
  year_id: number;
  block_ids: number[];
  subject_ids?: number[];
}

export interface OnboardingStatusResponse {
  status: string;
  message: string;
}

export interface UserProfileYear {
  id: number;
  slug: string;
  display_name: string;
}

export interface UserProfileBlock {
  id: number;
  code: string;
  display_name: string;
}

export interface UserProfileSubject {
  id: number;
  code: string | null;
  display_name: string;
}

export interface UserProfile {
  user_id: string;
  onboarding_completed: boolean;
  selected_year: UserProfileYear | null;
  selected_blocks: UserProfileBlock[];
  selected_subjects: UserProfileSubject[];
  created_at: string;
  updated_at: string | null;
}

// ============================================================================
// Existing Types
// ============================================================================

// ============================================================================
// Syllabus Types (New Structure)
// ============================================================================

export interface Year {
  id: number;
  name: string;
  order_no: number;
}

export interface Block {
  id: number;
  year_id: number;
  code: string;
  name: string;
  order_no: number;
}

export interface Theme {
  id: number;
  block_id: number;
  title: string;
  order_no: number;
  description?: string;
}

// Admin types
export interface YearAdmin extends Year {
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface BlockAdmin extends Block {
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ThemeAdmin extends Theme {
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Question {
  id: number;
  theme_id: number;
  question_text: string;
  options: string[];
  correct_option_index: number;
  explanation?: string;
  tags?: string[];
  difficulty?: string;
  is_published: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Session {
  id: number;
  user_id: string;
  question_count: number;
  time_limit_minutes: number;
  question_ids: number[];
  is_submitted: boolean;
  started_at: string;
  submitted_at?: string;
}

export interface AnswerSubmit {
  question_id: number;
  selected_option_index: number;
  is_marked_for_review: boolean;
}

export interface ReviewData {
  session_id: number;
  total_questions: number;
  correct_count: number;
  incorrect_count: number;
  score_percentage: number;
  questions: Array<{
    question_id: number;
    question_text: string;
    options: string[];
    correct_option_index: number;
    selected_option_index: number;
    is_correct: boolean;
    explanation?: string;
    is_marked_for_review: boolean;
  }>;
}

// Syllabus APIs (Student)
export const syllabusAPI = {
  getYears: async (): Promise<Year[]> => {
    const response = await fetch(`/api/syllabus/years`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load years");
    }

    return response.json();
  },
  getBlocks: async (year: string | number): Promise<Block[]> => {
    const params = `?year=${encodeURIComponent(year)}`;
    const response = await fetch(`/api/syllabus/blocks${params}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load blocks");
    }

    return response.json();
  },
  getThemes: async (blockId: number): Promise<Theme[]> => {
    // Validate blockId - must be a valid positive integer
    if (blockId === null || blockId === undefined || typeof blockId !== "number" || isNaN(blockId) || blockId <= 0) {
      throw new Error("Valid block ID is required");
    }
    const params = `?block_id=${blockId}`;
    const response = await fetch(`/api/syllabus/themes${params}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.error?.message || `Failed to load themes (${response.status})`;
      const error = new Error(errorMessage) as Error & { status: number; errorData: unknown };
      error.status = response.status;
      error.errorData = errorData;
      throw error;
    }

    return response.json();
  },
};

// Admin Syllabus APIs
export const adminSyllabusAPI = {
  // Years
  getYears: async (): Promise<YearAdmin[]> => {
    const response = await fetch(`/api/admin/syllabus/years`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load years");
    }
    return response.json();
  },
  createYear: async (data: { name: string; order_no: number; is_active?: boolean }): Promise<YearAdmin> => {
    const response = await fetch(`/api/admin/syllabus/years`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to create year");
    }
    return response.json();
  },
  updateYear: async (id: number, data: Partial<YearAdmin>): Promise<YearAdmin> => {
    const response = await fetch(`/api/admin/syllabus/years/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to update year");
    }
    return response.json();
  },
  enableYear: async (id: number): Promise<YearAdmin> => {
    const response = await fetch(`/api/admin/syllabus/years/${id}/enable`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to enable year");
    }
    return response.json();
  },
  disableYear: async (id: number): Promise<YearAdmin> => {
    const response = await fetch(`/api/admin/syllabus/years/${id}/disable`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to disable year");
    }
    return response.json();
  },
  // Blocks
  getBlocks: async (yearId: number): Promise<BlockAdmin[]> => {
    // Validate yearId - must be a valid positive integer
    if (yearId === null || yearId === undefined || typeof yearId !== "number" || isNaN(yearId) || yearId <= 0) {
      throw new Error("Valid year ID is required");
    }
    const response = await fetch(`/api/admin/syllabus/years/${yearId}/blocks`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.error?.message || `Failed to load blocks (${response.status})`;
      const error = new Error(errorMessage) as Error & { status: number; errorData: unknown };
      error.status = response.status;
      error.errorData = errorData;
      throw error;
    }
    return response.json();
  },
  createBlock: async (data: { year_id: number; code: string; name: string; order_no: number; is_active?: boolean }): Promise<BlockAdmin> => {
    const response = await fetch(`/api/admin/syllabus/blocks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to create block");
    }
    return response.json();
  },
  updateBlock: async (id: number, data: Partial<BlockAdmin>): Promise<BlockAdmin> => {
    const response = await fetch(`/api/admin/syllabus/blocks/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to update block");
    }
    return response.json();
  },
  enableBlock: async (id: number): Promise<BlockAdmin> => {
    const response = await fetch(`/api/admin/syllabus/blocks/${id}/enable`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to enable block");
    }
    return response.json();
  },
  disableBlock: async (id: number): Promise<BlockAdmin> => {
    const response = await fetch(`/api/admin/syllabus/blocks/${id}/disable`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to disable block");
    }
    return response.json();
  },
  reorderBlocks: async (yearId: number, orderedBlockIds: number[]): Promise<void> => {
    const response = await fetch(`/api/admin/syllabus/years/${yearId}/blocks/reorder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ ordered_block_ids: orderedBlockIds }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to reorder blocks");
    }
  },
  // Themes
  getThemes: async (blockId: number): Promise<ThemeAdmin[]> => {
    // Validate blockId - must be a valid positive integer
    if (blockId === null || blockId === undefined || typeof blockId !== "number" || isNaN(blockId) || blockId <= 0) {
      throw new Error("Valid block ID is required");
    }
    const response = await fetch(`/api/admin/syllabus/blocks/${blockId}/themes`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.error?.message || `Failed to load themes (${response.status})`;
      const error = new Error(errorMessage) as Error & { status: number; errorData: unknown };
      error.status = response.status;
      error.errorData = errorData;
      throw error;
    }
    return response.json();
  },
  createTheme: async (data: { block_id: number; title: string; order_no: number; description?: string; is_active?: boolean }): Promise<ThemeAdmin> => {
    const response = await fetch(`/api/admin/syllabus/themes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to create theme");
    }
    return response.json();
  },
  updateTheme: async (id: number, data: Partial<ThemeAdmin>): Promise<ThemeAdmin> => {
    const response = await fetch(`/api/admin/syllabus/themes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to update theme");
    }
    return response.json();
  },
  enableTheme: async (id: number): Promise<ThemeAdmin> => {
    const response = await fetch(`/api/admin/syllabus/themes/${id}/enable`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to enable theme");
    }
    return response.json();
  },
  disableTheme: async (id: number): Promise<ThemeAdmin> => {
    const response = await fetch(`/api/admin/syllabus/themes/${id}/disable`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to disable theme");
    }
    return response.json();
  },
  reorderThemes: async (blockId: number, orderedThemeIds: number[]): Promise<void> => {
    const response = await fetch(`/api/admin/syllabus/blocks/${blockId}/themes/reorder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ ordered_theme_ids: orderedThemeIds }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to reorder themes");
    }
  },
  // CSV Import/Export
  downloadTemplate: async (type: "years" | "blocks" | "themes"): Promise<Blob> => {
    const response = await fetch(`/api/admin/syllabus/import/templates/${type}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to download template");
    }
    return response.blob();
  },
  importCSV: async (
    type: "years" | "blocks" | "themes",
    file: File,
    dryRun: boolean,
    autoCreate: boolean
  ): Promise<{
    success: boolean;
    message?: string;
    rows_processed?: number;
    rows_failed?: number;
    errors?: Array<{ row: number; reason?: string; message?: string }>;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`/api/admin/syllabus/import/${type}?dry_run=${dryRun}&auto_create=${autoCreate}`, {
      method: "POST",
      credentials: "include",
      body: formData,
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to import CSV");
    }
    return response.json();
  },
};

// Admin APIs
export const adminAPI = {
  listQuestions: async (skip = 0, limit = 100, published?: boolean): Promise<Question[]> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (published !== undefined) params.set("published", published.toString());
    
    const response = await fetch(`/api/admin/questions?${params}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.error?.message || `Failed to load questions (${response.status})`;
      const error = new Error(errorMessage) as Error & { status: number; errorData: unknown };
      error.status = response.status;
      error.errorData = errorData;
      throw error;
    }
    return response.json();
  },
  
  getQuestion: async (id: number): Promise<Question> => {
    const response = await fetch(`/api/admin/questions/${id}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load question");
    }
    return response.json();
  },
  
  createQuestion: async (
    question: Omit<Question, "id" | "created_at" | "updated_at" | "is_published">,
  ): Promise<Question> => {
    const response = await fetch("/api/admin/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(question),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to create question");
    }
    return response.json();
  },
  
  updateQuestion: async (id: number, question: Partial<Question>): Promise<Question> => {
    const response = await fetch(`/api/admin/questions/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(question),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to update question");
    }
    return response.json();
  },
  
  publishQuestion: async (id: number): Promise<void> => {
    const response = await fetch(`/api/admin/questions/${id}/publish`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to publish question");
    }
  },
  
  unpublishQuestion: async (id: number): Promise<void> => {
    const response = await fetch(`/api/admin/questions/${id}/unpublish`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to unpublish question");
    }
  },
};

// Student APIs
export const studentAPI = {
  getQuestions: async (themeId?: number, blockId?: string, limit = 50): Promise<Question[]> => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (themeId) params.set("theme_id", themeId.toString());
    if (blockId) params.set("block_id", blockId);
    
    const response = await fetch(`/api/questions?${params}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load questions");
    }
    return response.json();
  },
  
  createSession: async (data: {
    theme_id?: number;
    block_id?: string;
    question_count?: number;
    time_limit_minutes?: number;
  }): Promise<Session> => {
    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to create session");
    }
    return response.json();
  },
  
  getSession: async (id: number): Promise<Session> => {
    const response = await fetch(`/api/sessions/${id}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load session");
    }
    return response.json();
  },
  
  submitAnswer: async (
    sessionId: number,
    answer: AnswerSubmit,
  ): Promise<{ message: string; is_correct: boolean }> => {
    const response = await fetch(`/api/sessions/${sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(answer),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to submit answer");
    }
    return response.json();
  },
  
  submitSession: async (
    sessionId: number,
  ): Promise<{ message: string; score: number; total: number; percentage: number }> => {
    const response = await fetch(`/api/sessions/${sessionId}/submit`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to submit session");
    }
    return response.json();
  },
  
  getReview: async (sessionId: number): Promise<ReviewData> => {
    const response = await fetch(`/api/sessions/${sessionId}/review`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load review");
    }
    return response.json();
  },
};

// Onboarding APIs
export const onboardingAPI = {
  /**
   * Get available onboarding options (years, blocks, subjects)
   * Uses BFF route to properly forward auth cookies
   */
  getOptions: async (): Promise<OnboardingOptions> => {
    const response = await fetch("/api/onboarding/options", {
      method: "GET",
      credentials: "include",
    });
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error?.message || "Failed to load options");
    }
    
    return response.json();
  },

  /**
   * Submit onboarding selections
   * Uses BFF route to properly forward auth cookies
   */
  submitOnboarding: async (data: OnboardingRequest): Promise<OnboardingStatusResponse> => {
    const response = await fetch("/api/onboarding/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to save preferences");
    }

    return response.json();
  },

  /**
   * Get current user's profile including onboarding status
   * Uses BFF route to properly forward auth cookies
   */
  getProfile: async (): Promise<UserProfile> => {
    const response = await fetch("/api/users/me/profile", {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load profile");
    }

    return response.json();
  },
};

// Allowed blocks API removed - platform is now fully self-paced
