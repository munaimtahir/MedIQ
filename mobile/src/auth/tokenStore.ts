/**Token storage and refresh management.*/

import * as SecureStore from "expo-secure-store";
import { RefreshRequest, RefreshResponse } from "../types/api";
import { apiClient } from "../api/client";

const REFRESH_TOKEN_KEY = "refresh_token";
const ACCESS_TOKEN_KEY = "access_token"; // In-memory only (not persisted)

// Refresh lock to prevent concurrent refreshes
let refreshLock: Promise<string | null> | null = null;

export class TokenStore {
  private accessToken: string | null = null;
  
  // Get access token (in-memory)
  getAccessToken(): string | null {
    return this.accessToken;
  }
  
  // Set tokens
  async setTokens(accessToken: string, refreshToken: string): Promise<void> {
    this.accessToken = accessToken;
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
    apiClient.setAccessToken(accessToken);
  }
  
  // Clear tokens
  async clearTokens(): Promise<void> {
    this.accessToken = null;
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    apiClient.setAccessToken(null);
  }
  
  // Get refresh token (from secure storage)
  async getRefreshToken(): Promise<string | null> {
    return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  }
  
  // Refresh tokens
  async refreshTokens(): Promise<string | null> {
    // Use refresh lock to prevent concurrent refreshes
    if (refreshLock) {
      return await refreshLock;
    }
    
    refreshLock = this._doRefresh();
    try {
      const newToken = await refreshLock;
      return newToken;
    } finally {
      refreshLock = null;
    }
  }
  
  private async _doRefresh(): Promise<string | null> {
    const refreshToken = await this.getRefreshToken();
    
    if (!refreshToken) {
      await this.clearTokens();
      return null;
    }
    
    try {
      const response = await apiClient.post<RefreshResponse>(
        "/auth/refresh",
        { refresh_token: refreshToken } as RefreshRequest
      );
      
      // Update tokens
      await this.setTokens(
        response.tokens.access_token,
        response.tokens.refresh_token
      );
      
      return response.tokens.access_token;
    } catch (error: any) {
      // Refresh failed - clear tokens
      await this.clearTokens();
      return null;
    }
  }
  
  // Initialize: set refresh callback on API client
  initialize(): void {
    apiClient.setRefreshTokenCallback(() => this.refreshTokens());
  }
}

// Singleton instance
export const tokenStore = new TokenStore();
tokenStore.initialize();
