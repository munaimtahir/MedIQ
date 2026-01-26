"use client";

import { useState, useEffect } from "react";

const ADMIN_SIDEBAR_COLLAPSED_KEY = "admin-sidebar-collapsed";

export function useAdminSidebarState() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    // Load initial state from localStorage
    const saved = localStorage.getItem(ADMIN_SIDEBAR_COLLAPSED_KEY);
    if (saved !== null) {
      setIsCollapsed(saved === "true");
    }

    // Listen for storage changes (cross-tab)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === ADMIN_SIDEBAR_COLLAPSED_KEY) {
        setIsCollapsed(e.newValue === "true");
      }
    };

    // Listen for custom event (same-tab)
    const handleCustomEvent = () => {
      const saved = localStorage.getItem(ADMIN_SIDEBAR_COLLAPSED_KEY);
      if (saved !== null) {
        setIsCollapsed(saved === "true");
      }
    };

    window.addEventListener("storage", handleStorageChange);
    window.addEventListener("admin-sidebar-toggle", handleCustomEvent);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("admin-sidebar-toggle", handleCustomEvent);
    };
  }, []);

  const toggle = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem(ADMIN_SIDEBAR_COLLAPSED_KEY, String(newState));
    // Dispatch custom event for same-tab updates
    window.dispatchEvent(new Event("admin-sidebar-toggle"));
  };

  return { isCollapsed, toggle };
}
