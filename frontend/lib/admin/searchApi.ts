/**
 * Admin Search API Client
 */

import type { SearchMetaResponse, SearchQueryParams, SearchResponse } from "@/lib/types/search";

/**
 * Build query string from SearchQueryParams
 */
function buildSearchQueryString(params: SearchQueryParams): string {
  const searchParams = new URLSearchParams();

  if (params.q) searchParams.set("q", params.q);
  if (params.year !== undefined) searchParams.set("year", params.year.toString());
  if (params.block_id) searchParams.set("block_id", params.block_id);
  if (params.theme_id) searchParams.set("theme_id", params.theme_id);
  if (params.topic_id) searchParams.set("topic_id", params.topic_id);
  if (params.concept_id && params.concept_id.length > 0) {
    params.concept_id.forEach((id) => searchParams.append("concept_id", id));
  }
  if (params.cognitive_level && params.cognitive_level.length > 0) {
    params.cognitive_level.forEach((level) => searchParams.append("cognitive_level", level));
  }
  if (params.difficulty_label && params.difficulty_label.length > 0) {
    params.difficulty_label.forEach((diff) => searchParams.append("difficulty_label", diff));
  }
  if (params.source_book && params.source_book.length > 0) {
    params.source_book.forEach((book) => searchParams.append("source_book", book));
  }
  if (params.status && params.status.length > 0) {
    params.status.forEach((s) => searchParams.append("status", s));
  }
  if (params.include_unpublished) searchParams.set("include_unpublished", "true");
  if (params.sort) searchParams.set("sort", params.sort);
  if (params.page) searchParams.set("page", params.page.toString());
  if (params.page_size) searchParams.set("page_size", params.page_size.toString());

  return searchParams.toString();
}

/**
 * Admin Search API
 */
export const adminSearchApi = {
  /**
   * Search questions with filters and facets
   */
  async searchQuestions(params: SearchQueryParams = {}): Promise<SearchResponse> {
    const queryString = buildSearchQueryString(params);
    const url = `/api/admin/questions/search${queryString ? `?${queryString}` : ""}`;

    const response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || errorData.detail || "Failed to search questions");
    }

    return response.json();
  },

  /**
   * Get search metadata
   */
  async getSearchMeta(): Promise<SearchMetaResponse> {
    const response = await fetch("/api/admin/questions/search/meta", {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error?.message || errorData.detail || "Failed to load search metadata",
      );
    }

    return response.json();
  },
};
