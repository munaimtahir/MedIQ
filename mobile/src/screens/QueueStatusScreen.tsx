/**Queue status screen showing sync queue diagnostics.*/

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  Alert,
} from "react-native";
import {
  getAttemptQueueStats,
  getRecentAttempts,
  resetRejectedToPending,
  AttemptQueueItem,
} from "../storage/db";

interface QueueStatusScreenProps {
  onBack: () => void;
}

export function QueueStatusScreen({ onBack }: QueueStatusScreenProps) {
  const [stats, setStats] = useState({
    pending: 0,
    sent: 0,
    acked: 0,
    duplicate: 0,
    rejected: 0,
  });
  const [recent, setRecent] = useState<AttemptQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const [statsData, recentData] = await Promise.all([
        getAttemptQueueStats(),
        getRecentAttempts(20),
      ]);
      setStats(statsData);
      setRecent(recentData);
    } catch (error: any) {
      Alert.alert("Error", error.message || "Failed to load queue status");
    } finally {
      setLoading(false);
    }
  };

  const handleResetRejected = async () => {
    Alert.alert(
      "Reset Rejected",
      "Reset all rejected attempts to pending?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Reset",
          onPress: async () => {
            try {
              setResetting(true);
              await resetRejectedToPending();
              await loadStatus();
              Alert.alert("Success", "Rejected attempts reset to pending");
            } catch (error: any) {
              Alert.alert("Error", error.message || "Failed to reset");
            } finally {
              setResetting(false);
            }
          },
        },
      ]
    );
  };

  const renderItem = ({ item }: { item: AttemptQueueItem }) => {
    const statusColor: Record<string, string> = {
      pending: "#ff9800",
      sent: "#2196f3",
      acked: "#4caf50",
      duplicate: "#9e9e9e",
      rejected: "#f44336",
    };

    return (
      <View style={styles.item}>
        <View style={styles.itemHeader}>
          <Text style={styles.itemId}>{item.client_attempt_id.substring(0, 8)}...</Text>
          <View
            style={[styles.statusBadge, { backgroundColor: statusColor[item.status] }]}
          >
            <Text style={styles.statusText}>{item.status.toUpperCase()}</Text>
          </View>
        </View>
        <Text style={styles.itemMeta}>
          Q: {item.question_id.substring(0, 8)}... • Retries: {item.retry_count}
        </Text>
        {item.last_error_code && (
          <Text style={styles.errorCode}>Error: {item.last_error_code}</Text>
        )}
        <Text style={styles.itemTime}>
          {new Date(item.created_at).toLocaleString()}
        </Text>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Queue Status</Text>
        <TouchableOpacity onPress={loadStatus}>
          <Text style={styles.refreshButton}>Refresh</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.statsContainer}>
        <View style={styles.statRow}>
          <View style={[styles.statBox, { backgroundColor: "#ff9800" }]}>
            <Text style={styles.statValue}>{stats.pending}</Text>
            <Text style={styles.statLabel}>Pending</Text>
          </View>
          <View style={[styles.statBox, { backgroundColor: "#2196f3" }]}>
            <Text style={styles.statValue}>{stats.sent}</Text>
            <Text style={styles.statLabel}>Sent</Text>
          </View>
          <View style={[styles.statBox, { backgroundColor: "#4caf50" }]}>
            <Text style={styles.statValue}>{stats.acked}</Text>
            <Text style={styles.statLabel}>Acked</Text>
          </View>
        </View>
        <View style={styles.statRow}>
          <View style={[styles.statBox, { backgroundColor: "#9e9e9e" }]}>
            <Text style={styles.statValue}>{stats.duplicate}</Text>
            <Text style={styles.statLabel}>Duplicate</Text>
          </View>
          <View style={[styles.statBox, { backgroundColor: "#f44336" }]}>
            <Text style={styles.statValue}>{stats.rejected}</Text>
            <Text style={styles.statLabel}>Rejected</Text>
          </View>
        </View>
      </View>

      {stats.rejected > 0 && (
        <TouchableOpacity
          style={[styles.resetButton, resetting && styles.resetButtonDisabled]}
          onPress={handleResetRejected}
          disabled={resetting}
        >
          {resetting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.resetButtonText}>Reset Rejected to Pending</Text>
          )}
        </TouchableOpacity>
      )}

      <Text style={styles.sectionTitle}>Recent Attempts (Last 20)</Text>
      <FlatList
        data={recent}
        renderItem={renderItem}
        keyExtractor={(item) => item.id.toString()}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No attempts in queue</Text>
        }
      />
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
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  backButton: {
    fontSize: 16,
    color: "#1976d2",
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
  },
  refreshButton: {
    fontSize: 16,
    color: "#1976d2",
  },
  statsContainer: {
    padding: 16,
  },
  statRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginBottom: 12,
  },
  statBox: {
    flex: 1,
    padding: 16,
    borderRadius: 8,
    marginHorizontal: 4,
    alignItems: "center",
  },
  statValue: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#fff",
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: "#fff",
    fontWeight: "600",
  },
  resetButton: {
    backgroundColor: "#ff9800",
    padding: 12,
    margin: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  resetButtonDisabled: {
    opacity: 0.6,
  },
  resetButtonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    padding: 16,
    paddingBottom: 8,
  },
  item: {
    backgroundColor: "#fff",
    padding: 12,
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 8,
  },
  itemHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  itemId: {
    fontSize: 12,
    fontFamily: "monospace",
    color: "#666",
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  statusText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "600",
  },
  itemMeta: {
    fontSize: 12,
    color: "#666",
    marginBottom: 4,
  },
  errorCode: {
    fontSize: 12,
    color: "#f44336",
    fontWeight: "600",
    marginBottom: 4,
  },
  itemTime: {
    fontSize: 10,
    color: "#999",
  },
  emptyText: {
    textAlign: "center",
    marginTop: 32,
    color: "#666",
  },
});
