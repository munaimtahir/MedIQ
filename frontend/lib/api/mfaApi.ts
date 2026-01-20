/**
 * MFA API Client
 * Handles two-factor authentication setup, verification, and management
 */

import { apiRequest } from './base';

export interface MFASetupResponse {
  qr_code_data_uri: string;
  secret: string;
  backup_codes: string[];
}

export interface MFAVerifyResponse {
  valid: boolean;
}

export interface MFACompleteResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: string;
  };
}

export interface MFARegenerateCodesResponse {
  backup_codes: string[];
}

/**
 * Initiate MFA setup - generates QR code and secret
 */
export async function setupMFA(): Promise<MFASetupResponse> {
  return apiRequest<MFASetupResponse>('/auth/mfa/totp/setup', {
    method: 'POST',
  });
}

/**
 * Verify TOTP code during setup
 */
export async function verifyMFASetup(code: string): Promise<MFAVerifyResponse> {
  return apiRequest<MFAVerifyResponse>('/auth/mfa/totp/verify', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

/**
 * Complete MFA setup and get new tokens
 */
export async function completeMFASetup(code: string): Promise<MFACompleteResponse> {
  return apiRequest<MFACompleteResponse>('/auth/mfa/totp/complete', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

/**
 * Disable MFA for the current user
 */
export async function disableMFA(code: string): Promise<void> {
  return apiRequest<void>('/auth/mfa/totp/disable', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

/**
 * Regenerate backup codes (requires current TOTP code)
 */
export async function regenerateBackupCodes(totp_code: string): Promise<MFARegenerateCodesResponse> {
  return apiRequest<MFARegenerateCodesResponse>('/auth/mfa/backup-code/regenerate', {
    method: 'POST',
    body: JSON.stringify({ totp_code }),
  });
}

/**
 * Check if user has MFA enabled
 */
export async function getMFAStatus(): Promise<{ enabled: boolean; enabled_at?: string }> {
  try {
    // This endpoint might not exist, so we'll check via auth/me
    const response = await fetch('/api/auth/me', {
      credentials: 'include',
    });
    
    if (!response.ok) {
      return { enabled: false };
    }
    
    const data = await response.json();
    return {
      enabled: data.user?.mfa_enabled || false,
      enabled_at: data.user?.mfa_enabled_at || undefined,
    };
  } catch {
    return { enabled: false };
  }
}
