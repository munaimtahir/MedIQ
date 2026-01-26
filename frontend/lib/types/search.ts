/**
 * Types for search endpoints
 * Matches backend schemas in backend/app/schemas/search.py
 */

export interface SearchResultItem {
  question_id: string;
  version_id: string | null;
  status: string;
  published_at: string | null;
  updated_at: string | null;
  year: number | null;
  block_id: string | null;
  theme_id: string | null;
  topic_id: string | null;
  cognitive_level: string | null;
  difficulty_label: string | null;
  source_book: string | null;
  source_page: number | null;
  stem_preview: string;
  explanation_preview: string;
  tags_preview: string;
  has_media: boolean;
}

export interface FacetItem {
  value: string | number;
  count: number;
}

export interface SearchResponse {
  engine: "elasticsearch" | "postgres";
  total: number;
  page: number;
  page_size: number;
  results: SearchResultItem[];
  facets: {
    year: FacetItem[];
    block_id: FacetItem[];
    theme_id: FacetItem[];
    cognitive_level: FacetItem[];
    difficulty_label: FacetItem[];
    source_book: FacetItem[];
    status: FacetItem[];
  };
  warnings: string[];
}

export interface SearchMetaResponse {
  limits: {
    max_page_size: number;
  };
  engine: {
    enabled: boolean;
    reachable: boolean;
  };
  defaults: {
    include_unpublished_default: boolean;
    status_defaults: string[];
  };
  sort_options: string[];
}

export interface SearchQueryParams {
  q?: string;
  year?: number;
  block_id?: string;
  theme_id?: string;
  topic_id?: string;
  concept_id?: string[];
  cognitive_level?: string[];
  difficulty_label?: string[];
  source_book?: string[];
  status?: string[];
  include_unpublished?: boolean;
  sort?: "relevance" | "published_at_desc" | "updated_at_desc";
  page?: number;
  page_size?: number;
}
