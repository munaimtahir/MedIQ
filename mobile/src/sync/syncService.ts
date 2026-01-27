/**Sync service for batch syncing offline attempts.*/

import { BatchSyncRequest, BatchSyncResponse, SyncAttemptItem } from "../types/api";
import { apiClient } from "../api/client";
import {
  getPendingAttemptsForSync,
  queueItemToSyncAttempt,
  markAsSent,
  markAsAcked,
  markAsDuplicate,
  markAsRejected,
} from "../offline/attemptQueue";

export interface SyncResult {
  success: boolean;
  synced: number;
  acked: number;
  duplicate: number;
  rejected: number;
  error: string | null;
}

// Check if device is online
async function isOnline(): Promise<boolean> {
  try {
    // Try to use NetInfo if available
    const NetInfo = require("@react-native-community/netinfo").default;
    const state = await NetInfo.fetch();
    return state.isConnected ?? false;
  } catch {
    // Fallback: try to fetch a small resource
    try {
      const response = await fetch("https://www.google.com/favicon.ico", {
        method: "HEAD",
        cache: "no-cache",
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Sync pending attempts
export async function syncNow(): Promise<SyncResult> {
  // Check connectivity
  if (!(await isOnline())) {
    return {
      success: false,
      synced: 0,
      acked: 0,
      duplicate: 0,
      rejected: 0,
      error: "offline",
    };
  }
  
  let totalSynced = 0;
  let totalAcked = 0;
  let totalDuplicate = 0;
  let totalRejected = 0;
  let lastError: string | null = null;
  
  const maxLoops = 10; // Prevent infinite loops
  let loopCount = 0;
  
  try {
    while (loopCount < maxLoops) {
      // Get pending attempts (batch size: 50)
      const pending = await getPendingAttemptsForSync(50);
      
      if (pending.length === 0) {
        break; // No more pending
      }
      
      // Convert to sync format
      const attempts: SyncAttemptItem[] = pending.map(queueItemToSyncAttempt);
      
      // Mark as sent (optimistic)
      for (const item of pending) {
        await markAsSent(item.client_attempt_id);
      }
      
      try {
        // Send batch
        const response = await apiClient.post<BatchSyncResponse>(
          "/sync/attempts:batch",
          { attempts } as BatchSyncRequest
        );
        
        // Process results
        for (const result of response.results) {
          totalSynced++;
          
          if (result.status === "acked") {
            await markAsAcked(result.client_attempt_id);
            totalAcked++;
          } else if (result.status === "duplicate") {
            await markAsDuplicate(result.client_attempt_id);
            totalDuplicate++;
          } else if (result.status === "rejected") {
            await markAsRejected(
              result.client_attempt_id,
              result.error_code || "UNKNOWN_ERROR"
            );
            totalRejected++;
            lastError = result.error_code || "UNKNOWN_ERROR";
          }
        }
      } catch (error: any) {
        // Batch failed - mark items back to pending (except if already acked/duplicate)
        // Note: In production, you might want more sophisticated retry logic
        lastError = error.error_code || error.message || "SYNC_ERROR";
        break; // Stop syncing on error
      }
      
      loopCount++;
    }
    
    return {
      success: totalRejected === 0,
      synced: totalSynced,
      acked: totalAcked,
      duplicate: totalDuplicate,
      rejected: totalRejected,
      error: lastError,
    };
  } catch (error: any) {
    return {
      success: false,
      synced: totalSynced,
      acked: totalAcked,
      duplicate: totalDuplicate,
      rejected: totalRejected,
      error: error.message || "SYNC_ERROR",
    };
  }
}
