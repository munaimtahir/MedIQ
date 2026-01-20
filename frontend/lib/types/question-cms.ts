/**
 * Types for Admin CMS Question Bank
 * Matches backend schemas in backend/app/schemas/question_cms.py
 */

// ============================================================================
// Enums
// ============================================================================

export type QuestionStatus = "DRAFT" | "IN_REVIEW" | "APPROVED" | "PUBLISHED";

export type ChangeKind = "CREATE" | "EDIT" | "STATUS_CHANGE" | "PUBLISH" | "UNPUBLISH" | "IMPORT";

export type MediaRole =
  | "STEM"
  | "EXPLANATION"
  | "OPTION_A"
  | "OPTION_B"
  | "OPTION_C"
  | "OPTION_D"
  | "OPTION_E";

export type CognitiveLevel = "REMEMBER" | "UNDERSTAND" | "APPLY" | "ANALYZE" | "EVALUATE" | "CREATE";

export type DifficultyLevel = "EASY" | "MEDIUM" | "HARD";

// ============================================================================
// Question Types
// ============================================================================

export interface QuestionBase {
  stem: string | null;
  option_a: string | null;
  option_b: string | null;
  option_c: string | null;
  option_d: string | null;
  option_e: string | null;
  correct_index: number | null; // 0-4
  explanation_md: string | null;
  year_id: number | null;
  block_id: number | null;
  theme_id: number | null;
  topic_id: number | null;
  concept_id: number | null;
  cognitive_level: string | null;
  difficulty: string | null;
  source_book: string | null;
  source_page: string | null;
  source_ref: string | null;
}

export interface QuestionCreate extends Partial<QuestionBase> {}

export interface QuestionUpdate extends Partial<QuestionBase> {}

export interface QuestionOut extends QuestionBase {
  id: string; // UUID
  status: QuestionStatus;
  created_by: string; // UUID
  updated_by: string; // UUID
  approved_by: string | null; // UUID
  approved_at: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface QuestionListItem {
  id: string; // UUID
  stem: string | null;
  status: QuestionStatus;
  year_id: number | null;
  block_id: number | null;
  theme_id: number | null;
  difficulty: string | null;
  cognitive_level: string | null;
  created_at: string;
  updated_at: string | null;
  // Extended fields for display (will be loaded from syllabus)
  year_name?: string;
  block_code?: string;
  block_name?: string;
  theme_title?: string;
  source_book?: string | null;
  source_page?: string | null;
  updated_by_name?: string;
}

// ============================================================================
// Workflow Types
// ============================================================================

export interface WorkflowActionOut {
  message: string;
  question_id: string; // UUID
  previous_status: QuestionStatus;
  new_status: QuestionStatus;
}

export interface RejectRequest {
  reason: string;
}

// ============================================================================
// Version Types
// ============================================================================

export interface VersionOut {
  id: string; // UUID
  question_id: string; // UUID
  version_no: number;
  snapshot: Record<string, unknown>;
  change_kind: ChangeKind;
  change_reason: string | null;
  changed_by: string; // UUID
  changed_at: string;
}

// ============================================================================
// Media Types
// ============================================================================

export interface MediaOut {
  id: string; // UUID
  storage_provider: string;
  path: string;
  mime_type: string;
  size_bytes: number;
  sha256: string | null;
  created_by: string; // UUID
  created_at: string;
}

export interface MediaAttachIn {
  media_id: string; // UUID
  role: MediaRole;
}

// ============================================================================
// Query Types
// ============================================================================

export interface QuestionListQuery {
  status?: QuestionStatus;
  year_id?: number;
  block_id?: number;
  theme_id?: number;
  difficulty?: string;
  cognitive_level?: string;
  source_book?: string;
  q?: string;
  page?: number;
  page_size?: number;
  sort?: string;
  order?: "asc" | "desc";
}

// ============================================================================
// Audit Types
// ============================================================================

export interface AuditLogItem {
  id: string; // UUID
  actor_user_id: string; // UUID
  action: string;
  entity_type: string;
  entity_id: string; // UUID
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  meta: Record<string, unknown> | null;
  created_at: string;
  // Extended for display
  actor_name?: string;
  actor_email?: string;
}

export interface AuditLogQuery {
  entity_type?: string;
  entity_id?: string;
  action?: string;
  actor_id?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}
