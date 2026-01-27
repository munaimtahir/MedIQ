/**Package download and management with ETag caching.*/

import * as FileSystem from "expo-file-system";
import { TestPackageListResponse, TestPackageOut, TestPackageListItem } from "../types/api";
import { apiClient } from "../api/client";
import { saveDownloadedPackage, getDownloadedPackage } from "../storage/db";

const PACKAGES_DIR = `${FileSystem.documentDirectory}packages/`;

// Ensure packages directory exists
async function ensurePackagesDir(): Promise<void> {
  const dirInfo = await FileSystem.getInfoAsync(PACKAGES_DIR);
  if (!dirInfo.exists) {
    await FileSystem.makeDirectoryAsync(PACKAGES_DIR, { intermediates: true });
  }
}

// List available packages
export async function listPackages(): Promise<TestPackageListItem[]> {
  const response = await apiClient.get<TestPackageListResponse>("/tests/packages");
  return response.items;
}

// Download package with ETag caching
export async function downloadPackage(packageId: string): Promise<{
  downloaded: boolean;
  updated: boolean;
  package: TestPackageOut | null;
}> {
  await ensurePackagesDir();
  
  // Get saved ETag if package exists locally
  const saved = await getDownloadedPackage(packageId);
  const etag = saved?.etag || null;
  
  // Prepare headers
  const headers: HeadersInit = {};
  if (etag) {
    headers["If-None-Match"] = etag;
  }
  
  try {
    // Use API client for authenticated request
    // Note: We need to handle 304 manually since apiClient throws on non-200
    const getApiBase = (): string => {
      if (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_API_BASE_URL) {
        return process.env.EXPO_PUBLIC_API_BASE_URL;
      }
      return "http://localhost:8000";
    };
    const API_BASE = getApiBase();
    const url = `${API_BASE}/api/v1/tests/packages/${packageId}`;
    const accessToken = apiClient.getAccessToken();
    
    const fetchHeaders: HeadersInit = {
      "Content-Type": "application/json",
      ...headers,
    };
    
    if (accessToken) {
      fetchHeaders["Authorization"] = `Bearer ${accessToken}`;
    }
    
    const response = await fetch(url, {
      method: "GET",
      headers: fetchHeaders,
    });
    
    // Check for 304 Not Modified
    if (response.status === 304) {
      // Package unchanged - load from local file
      if (saved) {
        const fileContent = await FileSystem.readAsStringAsync(saved.file_path);
        const packageData = JSON.parse(fileContent) as TestPackageOut;
        return {
          downloaded: false,
          updated: false,
          package: packageData,
        };
      }
    }
    
    // Package updated or new - download
    if (response.ok) {
      const packageData = await response.json() as TestPackageOut;
      const newEtag = response.headers.get("ETag");
      
      // Save to file
      const filePath = `${PACKAGES_DIR}${packageId}.json`;
      await FileSystem.writeAsStringAsync(filePath, JSON.stringify(packageData));
      
      // Save to database
      await saveDownloadedPackage(
        packageId,
        newEtag,
        filePath
      );
      
      return {
        downloaded: true,
        updated: saved !== null,
        package: packageData,
      };
    }
    
    // Handle error response
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Failed to download package: ${response.status}`);
    }
    
    throw new Error(`Failed to download package: ${response.status}`);
  } catch (error) {
    console.error("Package download error:", error);
    throw error;
  }
}

// Get local package
export async function getLocalPackage(
  packageId: string
): Promise<TestPackageOut | null> {
  const saved = await getDownloadedPackage(packageId);
  
  if (!saved) {
    return null;
  }
  
  try {
    const fileContent = await FileSystem.readAsStringAsync(saved.file_path);
    return JSON.parse(fileContent) as TestPackageOut;
  } catch (error) {
    console.error("Error loading local package:", error);
    return null;
  }
}

// Check if package is downloaded
export async function isPackageDownloaded(packageId: string): Promise<boolean> {
  const saved = await getDownloadedPackage(packageId);
  return saved !== null;
}
