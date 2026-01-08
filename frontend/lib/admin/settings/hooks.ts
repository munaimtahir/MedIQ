/**
 * Hooks for admin settings data fetching and operations.
 */

import { useState, useEffect, useCallback } from "react";
import { notify } from "@/lib/notify";

export interface PlatformSettings {
  general: {
    platform_name: string;
    platform_description: string;
    default_language: string;
    timezone: string;
    default_landing: string;
  };
  academic_defaults: {
    default_year_id: number | null;
    blocks_visibility_mode: string;
  };
  practice_defaults: {
    default_mode: string;
    timer_default: string;
    review_policy: string;
    allow_mixed_blocks: boolean;
    allow_any_block_anytime: boolean;
  };
  security: {
    access_token_minutes: number;
    refresh_token_days: number;
    force_logout_on_password_reset: boolean;
  };
  notifications: {
    password_reset_emails_enabled: boolean;
    practice_reminders_enabled: boolean;
    admin_alerts_enabled: boolean;
    inapp_announcements_enabled: boolean;
  };
  version: number;
}

export interface SettingsResponse {
  data: PlatformSettings;
  updated_at: string | null;
  updated_by_user_id: number | null;
}

export interface SystemInfo {
  environment: string;
  api_version: string;
  backend_version: string;
  db_connected: boolean;
  redis_connected: boolean | null;
}

export function useAdminSettings() {
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/settings", {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to load settings");
      }

      const data: SettingsResponse = await response.json();
      setSettings(data.data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load settings");
      setError(error);
      notify.error("Failed to load settings", error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const updateSettings = useCallback(async (newSettings: PlatformSettings) => {
    try {
      const response = await fetch("/api/admin/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ data: newSettings }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || "Failed to update settings");
      }

      const data: SettingsResponse = await response.json();
      setSettings(data.data);
      notify.success("Settings saved", "Platform settings updated successfully");
      return data;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update settings");
      notify.error("Failed to save settings", error.message);
      throw error;
    }
  }, []);

  return { settings, loading, error, refetch: loadSettings, updateSettings };
}

export function useSystemInfo() {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    loadInfo();
  }, []);

  const loadInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/system/info", {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to load system info");
      }

      const data: SystemInfo = await response.json();
      setInfo(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load system info");
      setError(error);
    } finally {
      setLoading(false);
    }
  };

  return { info, loading, error, refetch: loadInfo };
}
