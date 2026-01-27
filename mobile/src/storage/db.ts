/**SQLite database for offline storage.*/

import * as SQLite from "expo-sqlite";
import { DownloadedPackage, AttemptQueueItem } from "../types/storage";

let db: SQLite.SQLiteDatabase | null = null;

// Initialize database
export async function initDatabase(): Promise<void> {
  if (db) {
    return;
  }
  
  db = await SQLite.openDatabaseAsync("exam_prep.db");
  
  // Create tables
  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS downloaded_packages (
      package_id TEXT PRIMARY KEY,
      etag TEXT,
      file_path TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS attempt_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      client_attempt_id TEXT UNIQUE NOT NULL,
      idempotency_key TEXT UNIQUE NOT NULL,
      package_id TEXT NOT NULL,
      session_id TEXT,
      offline_session_id TEXT NOT NULL,
      question_id TEXT NOT NULL,
      selected_option_id TEXT NOT NULL,
      answered_at TEXT NOT NULL,
      payload_hash TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      retry_count INTEGER NOT NULL DEFAULT 0,
      last_error_code TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    
    CREATE INDEX IF NOT EXISTS idx_attempt_queue_status ON attempt_queue(status);
    CREATE INDEX IF NOT EXISTS idx_attempt_queue_created_at ON attempt_queue(created_at);
  `);
}

// Downloaded Packages
export async function saveDownloadedPackage(
  packageId: string,
  etag: string | null,
  filePath: string
): Promise<void> {
  if (!db) await initDatabase();
  
  await db!.runAsync(
    `INSERT OR REPLACE INTO downloaded_packages 
     (package_id, etag, file_path, updated_at) 
     VALUES (?, ?, ?, datetime('now'))`,
    [packageId, etag, filePath]
  );
}

export async function getDownloadedPackage(
  packageId: string
): Promise<DownloadedPackage | null> {
  if (!db) await initDatabase();
  
  const result = await db!.getFirstAsync<DownloadedPackage>(
    `SELECT * FROM downloaded_packages WHERE package_id = ?`,
    [packageId]
  );
  
  return result || null;
}

export async function listDownloadedPackages(): Promise<DownloadedPackage[]> {
  if (!db) await initDatabase();
  
  return await db!.getAllAsync<DownloadedPackage>(
    `SELECT * FROM downloaded_packages ORDER BY updated_at DESC`
  );
}

// Attempt Queue
export async function enqueueAttempt(
  attempt: Omit<AttemptQueueItem, "id" | "status" | "retry_count" | "last_error_code" | "created_at">
): Promise<number> {
  if (!db) await initDatabase();
  
  const result = await db!.runAsync(
    `INSERT INTO attempt_queue 
     (client_attempt_id, idempotency_key, package_id, session_id, offline_session_id, 
      question_id, selected_option_id, answered_at, payload_hash, status, retry_count)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)`,
    [
      attempt.client_attempt_id,
      attempt.idempotency_key,
      attempt.package_id,
      attempt.session_id,
      attempt.offline_session_id,
      attempt.question_id,
      attempt.selected_option_id,
      attempt.answered_at,
      attempt.payload_hash,
    ]
  );
  
  return result.lastInsertRowId;
}

export async function listPendingAttempts(limit: number = 50): Promise<AttemptQueueItem[]> {
  if (!db) await initDatabase();
  
  return await db!.getAllAsync<AttemptQueueItem>(
    `SELECT * FROM attempt_queue 
     WHERE status = 'pending' 
     ORDER BY created_at ASC 
     LIMIT ?`,
    [limit]
  );
}

export async function markAttemptSent(clientAttemptId: string): Promise<void> {
  if (!db) await initDatabase();
  
  await db!.runAsync(
    `UPDATE attempt_queue SET status = 'sent' WHERE client_attempt_id = ?`,
    [clientAttemptId]
  );
}

export async function markAttemptAcked(clientAttemptId: string): Promise<void> {
  if (!db) await initDatabase();
  
  await db!.runAsync(
    `UPDATE attempt_queue SET status = 'acked' WHERE client_attempt_id = ?`,
    [clientAttemptId]
  );
}

export async function markAttemptDuplicate(clientAttemptId: string): Promise<void> {
  if (!db) await initDatabase();
  
  await db!.runAsync(
    `UPDATE attempt_queue SET status = 'duplicate' WHERE client_attempt_id = ?`,
    [clientAttemptId]
  );
}

export async function markAttemptRejected(
  clientAttemptId: string,
  errorCode: string
): Promise<void> {
  if (!db) await initDatabase();
  
  await db!.runAsync(
    `UPDATE attempt_queue 
     SET status = 'rejected', last_error_code = ?, retry_count = retry_count + 1
     WHERE client_attempt_id = ?`,
    [errorCode, clientAttemptId]
  );
}

export async function getAttemptQueueStats(): Promise<{
  pending: number;
  sent: number;
  acked: number;
  duplicate: number;
  rejected: number;
}> {
  if (!db) await initDatabase();
  
  const result = await db!.getFirstAsync<{
    pending: number;
    sent: number;
    acked: number;
    duplicate: number;
    rejected: number;
  }>(
    `SELECT 
      SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
      SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
      SUM(CASE WHEN status = 'acked' THEN 1 ELSE 0 END) as acked,
      SUM(CASE WHEN status = 'duplicate' THEN 1 ELSE 0 END) as duplicate,
      SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
     FROM attempt_queue`
  );
  
  return result || {
    pending: 0,
    sent: 0,
    acked: 0,
    duplicate: 0,
    rejected: 0,
  };
}

export async function getRecentAttempts(limit: number = 20): Promise<AttemptQueueItem[]> {
  if (!db) await initDatabase();
  
  return await db!.getAllAsync<AttemptQueueItem>(
    `SELECT * FROM attempt_queue 
     ORDER BY created_at DESC 
     LIMIT ?`,
    [limit]
  );
}

export async function resetRejectedToPending(): Promise<void> {
  if (!db) await initDatabase();
  
  await db!.runAsync(
    `UPDATE attempt_queue 
     SET status = 'pending', retry_count = 0, last_error_code = NULL
     WHERE status = 'rejected' AND retry_count < 5`
  );
}
