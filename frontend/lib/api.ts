// Support both NEXT_PUBLIC_API_BASE_URL (preferred) and NEXT_PUBLIC_API_URL (legacy)
const API_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

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

export interface Block {
  id: string;
  name: string;
  year: number;
  description?: string;
}

export interface Theme {
  id: number;
  block_id: string;
  name: string;
  description?: string;
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

function getHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
  };
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  // Use fetcher wrapper for automatic token refresh
  const { default: fetcher } = await import("./fetcher");
  return fetcher<T>(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options?.headers,
    },
  });
}

// Syllabus APIs
export const syllabusAPI = {
  getBlocks: async (year?: number): Promise<Block[]> => {
    const params = year ? `?year=${year}` : "";
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
  getThemes: async (blockId?: string): Promise<Theme[]> => {
    const params = blockId ? `?block_id=${blockId}` : "";
    const response = await fetch(`/api/syllabus/themes${params}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || "Failed to load themes");
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
      throw new Error(errorData.error?.message || "Failed to load questions");
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
