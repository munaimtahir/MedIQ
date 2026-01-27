/**Attempt queue management for offline sync.*/

import { SyncAttemptItem } from "../types/api";
import {
  enqueueAttempt,
  listPendingAttempts,
  markAttemptSent,
  markAttemptAcked,
  markAttemptDuplicate,
  markAttemptRejected,
  AttemptQueueItem,
} from "../storage/db";
import { generateUUID } from "../utils/uuid";

// Compute payload hash (SHA-256)
async function computePayloadHash(payload: {
  question_id: string;
  selected_option_index: number;
  answered_at: string;
}): Promise<string> {
  const payloadJson = JSON.stringify(payload, Object.keys(payload).sort());
  
  // Use expo-crypto if available, otherwise fallback to simple hash
  try {
    const { digest } = require("expo-crypto");
    const hash = await digest("SHA256", payloadJson);
    return hash;
  } catch {
    // Fallback: use Web Crypto API (works in React Native with polyfill)
    try {
      const encoder = new TextEncoder();
      const data = encoder.encode(payloadJson);
      const hashBuffer = await crypto.subtle.digest("SHA-256", data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
      return hashHex;
    } catch {
      // Last resort: simple hash (not cryptographically secure, but works for demo)
      // In production, ensure expo-crypto is available
      let hash = 0;
      for (let i = 0; i < payloadJson.length; i++) {
        const char = payloadJson.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
      }
      return Math.abs(hash).toString(16);
    }
  }
}

// Enqueue a single attempt
export async function enqueueAttemptItem(
  packageId: string,
  offlineSessionId: string,
  questionId: string,
  selectedOptionIndex: number,
  answeredAt: string
): Promise<string> {
  // Generate IDs
  const clientAttemptId = generateUUID();
  const idempotencyKey = generateUUID();
  
  // Compute payload hash
  const payloadHash = await computePayloadHash({
    question_id: questionId,
    selected_option_index: selectedOptionIndex,
    answered_at: answeredAt,
  });
  
  // Enqueue
  await enqueueAttempt({
    client_attempt_id: clientAttemptId,
    idempotency_key: idempotencyKey,
    package_id: packageId,
    session_id: null,
    offline_session_id: offlineSessionId,
    question_id: questionId,
    selected_option_id: selectedOptionIndex.toString(),
    answered_at: answeredAt,
    payload_hash: payloadHash,
  });
  
  return clientAttemptId;
}

// Get pending attempts for sync
export async function getPendingAttemptsForSync(
  limit: number = 50
): Promise<AttemptQueueItem[]> {
  return await listPendingAttempts(limit);
}

// Convert queue item to sync attempt item
export function queueItemToSyncAttempt(item: AttemptQueueItem): SyncAttemptItem {
  return {
    client_attempt_id: item.client_attempt_id,
    idempotency_key: item.idempotency_key,
    session_id: item.session_id,
    offline_session_id: item.offline_session_id,
    question_id: item.question_id,
    selected_option_index: parseInt(item.selected_option_id, 10),
    answered_at: item.answered_at,
    payload_hash: item.payload_hash,
  };
}

// Mark attempt as sent
export async function markAsSent(clientAttemptId: string): Promise<void> {
  await markAttemptSent(clientAttemptId);
}

// Mark attempt as acked
export async function markAsAcked(clientAttemptId: string): Promise<void> {
  await markAttemptAcked(clientAttemptId);
}

// Mark attempt as duplicate
export async function markAsDuplicate(clientAttemptId: string): Promise<void> {
  await markAttemptDuplicate(clientAttemptId);
}

// Mark attempt as rejected
export async function markAsRejected(
  clientAttemptId: string,
  errorCode: string
): Promise<void> {
  await markAttemptRejected(clientAttemptId, errorCode);
}
