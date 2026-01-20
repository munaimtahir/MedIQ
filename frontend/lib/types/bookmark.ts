/**
 * Bookmark types
 */

export interface Bookmark {
  id: string;
  user_id: string;
  question_id: string;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface BookmarkWithQuestion extends Bookmark {
  question_stem: string;
  question_status: string;
  year_id: number | null;
  block_id: number | null;
  theme_id: number | null;
  difficulty: string | null;
  cognitive_level: string | null;
}

export interface CreateBookmarkRequest {
  question_id: string;
  notes?: string | null;
}

export interface UpdateBookmarkRequest {
  notes?: string | null;
}

export interface CheckBookmarkResponse {
  is_bookmarked: boolean;
  bookmark_id: string | null;
}
