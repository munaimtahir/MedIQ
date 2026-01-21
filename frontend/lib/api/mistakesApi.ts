/**
 * Mistakes API Client
 */

import fetcher from "../fetcher";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface BlockInfo {
  id: string;
  name: string;
}

export interface ThemeInfo {
  id: string;
  name: string;
}

export interface QuestionInfo {
  id: string;
  stem_preview: string;
}

export interface ThemeCount {
  theme: ThemeInfo;
  wrong: number;
}

export interface BlockCount {
  block: BlockInfo;
  wrong: number;
}

export interface MistakesSummaryResponse {
  range_days: number;
  total_wrong: number;
  counts_by_type: Record<string, number>;
  top_themes: ThemeCount[];
  top_blocks: BlockCount[];
}

export interface MistakeItem {
  created_at: string;
  mistake_type: string;
  severity: number;
  theme: ThemeInfo;
  block: BlockInfo;
  question: QuestionInfo;
  evidence: {
    time_spent_sec?: number;
    change_count?: number;
    blur_count?: number;
    remaining_sec_at_answer?: number;
    mark_for_review_used?: boolean;
    rule_fired?: string;
    thresholds?: Record<string, number>;
    [key: string]: unknown;
  };
}

export interface MistakesListResponse {
  page: number;
  page_size: number;
  total: number;
  items: MistakeItem[];
}

/**
 * Get mistakes summary
 */
export async function getMistakesSummary(rangeDays: number = 30): Promise<MistakesSummaryResponse> {
  const params = new URLSearchParams({
    range_days: rangeDays.toString(),
  });

  return fetcher<MistakesSummaryResponse>(`${API_BASE}/v1/mistakes/summary?${params}`);
}

/**
 * Get paginated list of mistakes
 */
export async function getMistakesList(params: {
  rangeDays?: number;
  blockId?: string;
  themeId?: string;
  mistakeType?: string;
  page?: number;
  pageSize?: number;
}): Promise<MistakesListResponse> {
  const searchParams = new URLSearchParams();

  if (params.rangeDays) searchParams.set("range_days", params.rangeDays.toString());
  if (params.blockId) searchParams.set("block_id", params.blockId);
  if (params.themeId) searchParams.set("theme_id", params.themeId);
  if (params.mistakeType) searchParams.set("mistake_type", params.mistakeType);
  if (params.page) searchParams.set("page", params.page.toString());
  if (params.pageSize) searchParams.set("page_size", params.pageSize.toString());

  return fetcher<MistakesListResponse>(`${API_BASE}/v1/mistakes/list?${searchParams}`);
}
