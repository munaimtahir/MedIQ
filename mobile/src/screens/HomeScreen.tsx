/**Home screen with navigation menu.*/

import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";

interface HomeScreenProps {
  onNavigate: (screen: string) => void;
  onLogout: () => void;
}

export function HomeScreen({ onNavigate, onLogout }: HomeScreenProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Home</Text>

      <TouchableOpacity
        style={styles.button}
        onPress={() => onNavigate("Packages")}
      >
        <Text style={styles.buttonText}>Download Packages</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.button}
        onPress={() => onNavigate("OfflineAttempt")}
      >
        <Text style={styles.buttonText}>Offline Attempt Demo</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.button}
        onPress={() => onNavigate("Sync")}
      >
        <Text style={styles.buttonText}>Sync Now</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.button}
        onPress={() => onNavigate("QueueStatus")}
      >
        <Text style={styles.buttonText}>Queue Status</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[styles.button, styles.logoutButton]} onPress={onLogout}>
        <Text style={styles.buttonText}>Logout</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: "#f5f5f5",
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 32,
    textAlign: "center",
  },
  button: {
    backgroundColor: "#1976d2",
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    alignItems: "center",
  },
  logoutButton: {
    backgroundColor: "#d32f2f",
    marginTop: 32,
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
