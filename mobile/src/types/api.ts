/**API response types matching backend contracts (Tasks 172-174).*/

export interface ErrorResponse {
  error_code: string;
  message: string;
  details: unknown | null;
  request_id: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokensResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  user: {
    id: string;
    email: string;
    role: string;
  };
  tokens: TokensResponse;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  tokens: TokensResponse;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface StatusResponse {
  status: string;
}

// Test Package types
export interface PackageScopeData {
  year_id: number | null;
  block_id: number | null;
  theme_id: number | null;
}

export interface TestPackageListItem {
  package_id: string;
  name: string;
  scope: string;
  scope_data: PackageScopeData;
  version: number;
  version_hash: string;
  updated_at: string;
}

export interface TestPackageListResponse {
  items: TestPackageListItem[];
}

export interface QuestionSnapshot {
  question_id: string;
  stem: string;
  option_a: string | null;
  option_b: string | null;
  option_c: string | null;
  option_d: string | null;
  option_e: string | null;
  correct_index: number;
  explanation_md: string | null;
  year_id: number | null;
  block_id: number | null;
  theme_id: number | null;
  cognitive_level: string | null;
  difficulty: string | null;
}

export interface TestPackageOut {
  package_id: string;
  name: string;
  description: string | null;
  scope: string;
  scope_data: PackageScopeData;
  version: number;
  version_hash: string;
  questions: QuestionSnapshot[];
  created_at: string;
  updated_at: string | null;
  published_at: string | null;
}

// Sync types
export interface SyncAttemptItem {
  client_attempt_id: string;
  idempotency_key: string;
  session_id: string | null;
  offline_session_id: string | null;
  question_id: string;
  selected_option_index: number;
  answered_at: string;
  payload_hash: string;
}

export interface BatchSyncRequest {
  attempts: SyncAttemptItem[];
}

export interface SyncAttemptResult {
  client_attempt_id: string;
  status: "acked" | "duplicate" | "rejected";
  error_code: string | null;
  message: string | null;
  server_attempt_id: string | null;
  server_session_id: string | null;
}

export interface BatchSyncResponse {
  results: SyncAttemptResult[];
}
