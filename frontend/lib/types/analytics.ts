/**
 * Analytics types for student performance tracking
 */

export interface BlockSummary {
  block_id: number;
  block_name: string;
  attempted: number;
  correct: number;
  accuracy_pct: number;
}

export interface ThemeSummary {
  theme_id: number;
  theme_name: string;
  attempted: number;
  correct: number;
  accuracy_pct: number;
}

export interface DailyTrend {
  date: string;
  attempted: number;
  correct: number;
  accuracy_pct: number;
}

export interface LastSessionSummary {
  session_id: string;
  score_pct: number;
  submitted_at: string;
}

export interface AnalyticsOverview {
  sessions_completed: number;
  questions_seen: number;
  questions_answered: number;
  correct: number;
  accuracy_pct: number;
  avg_time_sec_per_question: number | null;
  by_block: BlockSummary[];
  weakest_themes: ThemeSummary[];
  trend: DailyTrend[];
  last_session: LastSessionSummary | null;
}

export interface BlockAnalytics {
  block_id: number;
  block_name: string;
  attempted: number;
  correct: number;
  accuracy_pct: number;
  themes: ThemeSummary[];
  trend: DailyTrend[];
}

export interface ThemeAnalytics {
  theme_id: number;
  theme_name: string;
  block_id: number;
  block_name: string;
  attempted: number;
  correct: number;
  accuracy_pct: number;
  trend: DailyTrend[];
  common_mistakes: any[];
}
