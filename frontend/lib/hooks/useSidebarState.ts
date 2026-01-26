"use client";

import { useState, useEffect } from "react";

const SIDEBAR_COLLAPSED_KEY = "student-sidebar-collapsed";

export function useSidebarState() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    // Load initial state from localStorage
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    if (saved !== null) {
      setIsCollapsed(saved === "true");
    }

    // Listen for storage changes (cross-tab)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === SIDEBAR_COLLAPSED_KEY) {
        setIsCollapsed(e.newValue === "true");
      }
    };

    // Listen for custom event (same-tab)
    const handleCustomEvent = () => {
      const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
      if (saved !== null) {
        setIsCollapsed(saved === "true");
      }
    };

    window.addEventListener("storage", handleStorageChange);
    window.addEventListener("sidebar-toggle", handleCustomEvent);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("sidebar-toggle", handleCustomEvent);
    };
  }, []);

  const toggle = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(newState));
    // Dispatch custom event for same-tab updates
    window.dispatchEvent(new Event("sidebar-toggle"));
  };

  return { isCollapsed, toggle };
}
