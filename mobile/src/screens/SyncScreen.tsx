/**Sync screen for syncing offline attempts.*/

import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { syncNow, SyncResult } from "../sync/syncService";

interface SyncScreenProps {
  onBack: () => void;
}

export function SyncScreen({ onBack }: SyncScreenProps) {
  const [syncing, setSyncing] = useState(false);
  const [lastResult, setLastResult] = useState<SyncResult | null>(null);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);

  const handleSync = async () => {
    try {
      setSyncing(true);
      const result = await syncNow();
      setLastResult(result);
      setLastSyncTime(new Date());
    } catch (error: any) {
      setLastResult({
        success: false,
        synced: 0,
        acked: 0,
        duplicate: 0,
        rejected: 0,
        error: error.message || "SYNC_ERROR",
      });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Sync</Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Sync Status</Text>
          {lastSyncTime && (
            <Text style={styles.lastSync}>
              Last sync: {lastSyncTime.toLocaleString()}
            </Text>
          )}
        </View>

        {lastResult && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Last Sync Result</Text>
            <View
              style={[
                styles.resultBox,
                lastResult.success ? styles.resultSuccess : styles.resultError,
              ]}
            >
              <Text style={styles.resultTitle}>
                {lastResult.success ? "✓ Success" : "✗ Failed"}
              </Text>
              <Text style={styles.resultText}>
                Synced: {lastResult.synced}
              </Text>
              <Text style={styles.resultText}>
                Acked: {lastResult.acked}
              </Text>
              <Text style={styles.resultText}>
                Duplicate: {lastResult.duplicate}
              </Text>
              <Text style={styles.resultText}>
                Rejected: {lastResult.rejected}
              </Text>
              {lastResult.error && (
                <Text style={styles.errorText}>Error: {lastResult.error}</Text>
              )}
            </View>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Instructions</Text>
          <Text style={styles.instructionText}>
            • Tap "Sync Now" to sync pending attempts
          </Text>
          <Text style={styles.instructionText}>
            • Requires internet connection
          </Text>
          <Text style={styles.instructionText}>
            • Synced attempts are marked as acked/duplicate
          </Text>
          <Text style={styles.instructionText}>
            • Rejected attempts can be reset from Queue Status
          </Text>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.syncButton, syncing && styles.syncButtonDisabled]}
          onPress={handleSync}
          disabled={syncing}
        >
          {syncing ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.syncButtonText}>Sync Now</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  header: {
    padding: 20,
    backgroundColor: "#fff",
    borderBottomWidth: 1,
    borderBottomColor: "#ddd",
  },
  backButton: {
    fontSize: 16,
    color: "#1976d2",
    marginBottom: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
  },
  content: {
    flex: 1,
  },
  section: {
    backgroundColor: "#fff",
    padding: 16,
    margin: 16,
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 12,
  },
  lastSync: {
    fontSize: 14,
    color: "#666",
  },
  resultBox: {
    padding: 12,
    borderRadius: 6,
    marginTop: 8,
  },
  resultSuccess: {
    backgroundColor: "#e8f5e9",
  },
  resultError: {
    backgroundColor: "#ffebee",
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
  },
  resultText: {
    fontSize: 14,
    marginBottom: 4,
  },
  errorText: {
    fontSize: 14,
    color: "#d32f2f",
    fontWeight: "600",
    marginTop: 8,
  },
  instructionText: {
    fontSize: 14,
    color: "#666",
    marginBottom: 8,
    lineHeight: 20,
  },
  footer: {
    padding: 16,
    backgroundColor: "#fff",
    borderTopWidth: 1,
    borderTopColor: "#ddd",
  },
  syncButton: {
    backgroundColor: "#4caf50",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  syncButtonDisabled: {
    opacity: 0.6,
  },
  syncButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
