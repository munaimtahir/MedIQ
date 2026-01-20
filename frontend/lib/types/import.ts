/**
 * Types for Import System
 * Matches backend schemas in backend/app/schemas/import_schema.py
 */

// ============================================================================
// Enums
// ============================================================================

export type ImportFileType = "csv" | "json";

export type ImportJobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

// ============================================================================
// Import Schema Types
// ============================================================================

export interface ImportSchemaBase {
  name: string;
  file_type: ImportFileType;
  delimiter: string;
  quote_char: string;
  has_header: boolean;
  encoding: string;
  mapping_json: Record<string, any>;
  rules_json: Record<string, any>;
}

export interface ImportSchemaCreate extends ImportSchemaBase {}

export interface ImportSchemaUpdate {
  name?: string;
  file_type?: ImportFileType;
  delimiter?: string;
  quote_char?: string;
  has_header?: boolean;
  encoding?: string;
  mapping_json?: Record<string, any>;
  rules_json?: Record<string, any>;
}

export interface ImportSchemaOut extends ImportSchemaBase {
  id: string;
  version: number;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ImportSchemaListItem {
  id: string;
  name: string;
  version: number;
  is_active: boolean;
  file_type: ImportFileType;
  created_at: string;
  updated_at: string | null;
}

// ============================================================================
// Import Job Types
// ============================================================================

export interface ImportJobOut {
  id: string;
  schema_id: string | null;
  schema_name: string;
  schema_version: number;
  created_by: string;
  filename: string;
  file_type: ImportFileType;
  dry_run: boolean;
  status: ImportJobStatus;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  summary_json: Record<string, any> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ImportJobListItem {
  id: string;
  schema_name: string;
  schema_version: number;
  filename: string;
  dry_run: boolean;
  status: ImportJobStatus;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  created_at: string;
  completed_at: string | null;
}

export interface ImportJobResultOut {
  job_id: string;
  status: ImportJobStatus;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  summary_json: Record<string, any> | null;
}

export interface ImportJobRowOut {
  id: string;
  job_id: string;
  row_number: number;
  external_id: string | null;
  raw_row_json: Record<string, any>;
  errors_json: Array<{
    code: string;
    message: string;
    field: string | null;
  }>;
  created_at: string;
}

// ============================================================================
// Response Types
// ============================================================================

export interface ActivateSchemaResponse {
  message: string;
  schema_id: string;
  is_active: boolean;
}
