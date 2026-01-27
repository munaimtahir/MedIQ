/**SQLite database types.*/

export interface DownloadedPackage {
  package_id: string;
  etag: string | null;
  file_path: string;
  updated_at: string;
}

export interface AttemptQueueItem {
  id: number;
  client_attempt_id: string;
  idempotency_key: string;
  package_id: string;
  session_id: string | null;
  offline_session_id: string;
  question_id: string;
  selected_option_id: string;
  answered_at: string;
  payload_hash: string;
  status: "pending" | "sent" | "acked" | "duplicate" | "rejected";
  retry_count: number;
  last_error_code: string | null;
  created_at: string;
}
