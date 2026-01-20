/**
 * Session types for test engine v1
 */

export type SessionMode = "TUTOR" | "EXAM";
export type SessionStatus = "ACTIVE" | "SUBMITTED" | "EXPIRED";

// ============================================================================
// Request Types
// ============================================================================

export interface CreateSessionRequest {
  mode: SessionMode;
  year: number;
  blocks: string[];
  themes?: number[] | null;
  count: number;
  duration_seconds?: number | null;
  difficulty?: string[] | null;
  cognitive?: string[] | null;
}

export interface SubmitAnswerRequest {
  question_id: string;
  selected_index?: number | null;
  marked_for_review?: boolean | null;
}

// ============================================================================
// Response Types
// ============================================================================

export interface SessionProgress {
  answered_count: number;
  marked_for_review_count: number;
  current_position: number;
}

export interface SessionQuestionSummary {
  position: number;
  question_id: string;
  has_answer: boolean;
  marked_for_review: boolean;
}

export interface CurrentQuestion {
  question_id: string;
  position: number;
  stem: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  option_e: string;
  year_id?: number | null;
  block_id?: number | null;
  theme_id?: number | null;
}

export interface SessionMeta {
  id: string;
  user_id: string;
  mode: SessionMode;
  status: SessionStatus;
  year: number;
  blocks_json: string[];
  themes_json: number[] | null;
  total_questions: number;
  started_at: string;
  submitted_at: string | null;
  duration_seconds: number | null;
  expires_at: string | null;
  score_correct: number | null;
  score_total: number | null;
  score_pct: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface SessionState {
  session: SessionMeta;
  progress: SessionProgress;
  questions: SessionQuestionSummary[];
  current_question?: CurrentQuestion | null;
}

export interface CreateSessionResponse {
  session_id: string;
  status: SessionStatus;
  mode: SessionMode;
  total_questions: number;
  started_at: string;
  expires_at: string | null;
  progress: SessionProgress;
}

export interface Answer {
  id: string;
  session_id: string;
  question_id: string;
  selected_index: number | null;
  is_correct: boolean | null;
  answered_at: string | null;
  changed_count: number;
  marked_for_review: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface SubmitAnswerResponse {
  answer: Answer;
  progress: SessionProgress;
}

export interface SubmitSessionResponse {
  session_id: string;
  status: SessionStatus;
  score_correct: number;
  score_total: number;
  score_pct: number;
  submitted_at: string;
}

// ============================================================================
// Review Types
// ============================================================================

export interface ReviewQuestionContent {
  question_id: string;
  position: number;
  stem: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  option_e: string;
  correct_index: number;
  explanation_md: string | null;
  year_id?: number | null;
  block_id?: number | null;
  theme_id?: number | null;
  source_book?: string | null;
  source_page?: string | null;
}

export interface ReviewAnswer {
  question_id: string;
  selected_index: number | null;
  is_correct: boolean | null;
  marked_for_review: boolean;
  answered_at: string | null;
  changed_count: number;
}

export interface ReviewItem {
  question: ReviewQuestionContent;
  answer: ReviewAnswer;
}

export interface SessionReview {
  session: SessionMeta;
  items: ReviewItem[];
}
