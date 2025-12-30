const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const userId = typeof window !== "undefined" ? localStorage.getItem("userId") : null;
  return {
    "Content-Type": "application/json",
    ...(userId && { "X-User-Id": userId }),
  };
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Syllabus APIs
export const syllabusAPI = {
  getBlocks: (year?: number): Promise<Block[]> => {
    const params = year ? `?year=${year}` : "";
    return fetchAPI<Block[]>(`/blocks${params}`);
  },
  getThemes: (blockId?: string): Promise<Theme[]> => {
    const params = blockId ? `?block_id=${blockId}` : "";
    return fetchAPI<Theme[]>(`/themes${params}`);
  },
};

// Admin APIs
export const adminAPI = {
  listQuestions: (skip = 0, limit = 100, published?: boolean): Promise<Question[]> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
      ...(published !== undefined && { published: published.toString() }),
    });
    return fetchAPI<Question[]>(`/admin/questions?${params}`);
  },
  getQuestion: (id: number): Promise<Question> => {
    return fetchAPI<Question>(`/admin/questions/${id}`);
  },
  createQuestion: (
    question: Omit<Question, "id" | "created_at" | "updated_at" | "is_published">,
  ): Promise<Question> => {
    return fetchAPI<Question>("/admin/questions", {
      method: "POST",
      body: JSON.stringify(question),
    });
  },
  updateQuestion: (id: number, question: Partial<Question>): Promise<Question> => {
    return fetchAPI<Question>(`/admin/questions/${id}`, {
      method: "PUT",
      body: JSON.stringify(question),
    });
  },
  publishQuestion: (id: number): Promise<void> => {
    return fetchAPI(`/admin/questions/${id}/publish`, { method: "POST" });
  },
  unpublishQuestion: (id: number): Promise<void> => {
    return fetchAPI(`/admin/questions/${id}/unpublish`, { method: "POST" });
  },
};

// Student APIs
export const studentAPI = {
  getQuestions: (themeId?: number, blockId?: string, limit = 50): Promise<Question[]> => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      ...(themeId && { theme_id: themeId.toString() }),
      ...(blockId && { block_id: blockId }),
    });
    return fetchAPI<Question[]>(`/questions?${params}`);
  },
  createSession: (data: {
    theme_id?: number;
    block_id?: string;
    question_count?: number;
    time_limit_minutes?: number;
  }): Promise<Session> => {
    return fetchAPI<Session>("/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  getSession: (id: number): Promise<Session> => {
    return fetchAPI<Session>(`/sessions/${id}`);
  },
  submitAnswer: (
    sessionId: number,
    answer: AnswerSubmit,
  ): Promise<{ message: string; is_correct: boolean }> => {
    return fetchAPI(`/sessions/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify(answer),
    });
  },
  submitSession: (
    sessionId: number,
  ): Promise<{ message: string; score: number; total: number; percentage: number }> => {
    return fetchAPI(`/sessions/${sessionId}/submit`, {
      method: "POST",
    });
  },
  getReview: (sessionId: number): Promise<ReviewData> => {
    return fetchAPI<ReviewData>(`/sessions/${sessionId}/review`);
  },
};
