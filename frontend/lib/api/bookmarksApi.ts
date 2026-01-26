/**
 * Bookmarks API client
 * Uses BFF /api/v1 routes so auth cookies are sent (same-origin).
 */

import fetcher from "../fetcher";
import type {
  Bookmark,
  BookmarkWithQuestion,
  CreateBookmarkRequest,
  UpdateBookmarkRequest,
  CheckBookmarkResponse,
} from "../types/bookmark";

const API_BASE = "/api/v1";

/**
 * List all bookmarks for current user
 */
export async function listBookmarks(skip = 0, limit = 100): Promise<BookmarkWithQuestion[]> {
  return fetcher<BookmarkWithQuestion[]>(`${API_BASE}/bookmarks?skip=${skip}&limit=${limit}`, {
    method: "GET",
  });
}

/**
 * Create a new bookmark
 */
export async function createBookmark(payload: CreateBookmarkRequest): Promise<Bookmark> {
  return fetcher<Bookmark>(`${API_BASE}/bookmarks`, {
    method: "POST",
    body: payload,
  });
}

/**
 * Get a specific bookmark
 */
export async function getBookmark(bookmarkId: string): Promise<Bookmark> {
  return fetcher<Bookmark>(`${API_BASE}/bookmarks/${bookmarkId}`, {
    method: "GET",
  });
}

/**
 * Update a bookmark's notes
 */
export async function updateBookmark(
  bookmarkId: string,
  payload: UpdateBookmarkRequest,
): Promise<Bookmark> {
  return fetcher<Bookmark>(`${API_BASE}/bookmarks/${bookmarkId}`, {
    method: "PATCH",
    body: payload,
  });
}

/**
 * Delete a bookmark
 */
export async function deleteBookmark(bookmarkId: string): Promise<void> {
  await fetcher<void>(`${API_BASE}/bookmarks/${bookmarkId}`, {
    method: "DELETE",
  });
}

/**
 * Check if a question is bookmarked
 */
export async function checkBookmark(questionId: string): Promise<CheckBookmarkResponse> {
  return fetcher<CheckBookmarkResponse>(`${API_BASE}/bookmarks/check/${questionId}`, {
    method: "GET",
  });
}
