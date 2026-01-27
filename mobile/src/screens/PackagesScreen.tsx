/**Packages screen for downloading test packages.*/

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
import { TestPackageListItem } from "../types/api";
import { listPackages, downloadPackage, isPackageDownloaded } from "../offline/packageManager";

interface PackagesScreenProps {
  onBack: () => void;
}

export function PackagesScreen({ onBack }: PackagesScreenProps) {
  const [packages, setPackages] = useState<TestPackageListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadPackages();
    checkDownloaded();
  }, []);

  const loadPackages = async () => {
    try {
      setLoading(true);
      const items = await listPackages();
      setPackages(items);
    } catch (error: any) {
      Alert.alert("Error", error.message || "Failed to load packages");
    } finally {
      setLoading(false);
    }
  };

  const checkDownloaded = async () => {
    const downloadedSet = new Set<string>();
    for (const pkg of packages) {
      if (await isPackageDownloaded(pkg.package_id)) {
        downloadedSet.add(pkg.package_id);
      }
    }
    setDownloaded(downloadedSet);
  };

  const handleDownload = async (packageId: string) => {
    try {
      setDownloading(packageId);
      const result = await downloadPackage(packageId);

      if (result.downloaded) {
        Alert.alert(
          "Success",
          result.updated ? "Package updated" : "Package downloaded"
        );
        setDownloaded(new Set([...downloaded, packageId]));
      } else {
        Alert.alert("Info", "Package already up to date (304 Not Modified)");
      }
    } catch (error: any) {
      Alert.alert("Error", error.message || "Failed to download package");
    } finally {
      setDownloading(null);
    }
  };

  const renderPackage = ({ item }: { item: TestPackageListItem }) => {
    const isDownloaded = downloaded.has(item.package_id);
    const isDownloading = downloading === item.package_id;

    return (
      <View style={styles.packageItem}>
        <View style={styles.packageInfo}>
          <Text style={styles.packageName}>{item.name}</Text>
          <Text style={styles.packageMeta}>
            {item.scope} • v{item.version}
          </Text>
          {isDownloaded && <Text style={styles.downloadedBadge}>Downloaded</Text>}
        </View>
        <TouchableOpacity
          style={[styles.downloadButton, isDownloading && styles.downloadButtonDisabled]}
          onPress={() => handleDownload(item.package_id)}
          disabled={isDownloading}
        >
          {isDownloading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.downloadButtonText}>
              {isDownloaded ? "Update" : "Download"}
            </Text>
          )}
        </TouchableOpacity>
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
        <Text style={styles.title}>Test Packages</Text>
      </View>

      <FlatList
        data={packages}
        renderItem={renderPackage}
        keyExtractor={(item) => item.package_id}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No packages available</Text>
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
  packageItem: {
    backgroundColor: "#fff",
    padding: 16,
    marginBottom: 8,
    marginHorizontal: 16,
    marginTop: 8,
    borderRadius: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  packageInfo: {
    flex: 1,
  },
  packageName: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 4,
  },
  packageMeta: {
    fontSize: 12,
    color: "#666",
    marginBottom: 4,
  },
  downloadedBadge: {
    fontSize: 12,
    color: "#4caf50",
    fontWeight: "600",
  },
  downloadButton: {
    backgroundColor: "#1976d2",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  downloadButtonDisabled: {
    opacity: 0.6,
  },
  downloadButtonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  emptyText: {
    textAlign: "center",
    marginTop: 32,
    color: "#666",
  },
});
