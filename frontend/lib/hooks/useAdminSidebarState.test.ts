import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAdminSidebarState } from "./useAdminSidebarState";

describe("useAdminSidebarState", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("should initialize with collapsed=false by default", () => {
    const { result } = renderHook(() => useAdminSidebarState());
    expect(result.current.isCollapsed).toBe(false);
  });

  it("should load initial state from localStorage", () => {
    localStorage.setItem("admin-sidebar-collapsed", "true");
    const { result } = renderHook(() => useAdminSidebarState());
    expect(result.current.isCollapsed).toBe(true);
  });

  it("should toggle collapsed state", () => {
    const { result } = renderHook(() => useAdminSidebarState());
    
    expect(result.current.isCollapsed).toBe(false);
    
    act(() => {
      result.current.toggle();
    });
    
    expect(result.current.isCollapsed).toBe(true);
    expect(localStorage.getItem("admin-sidebar-collapsed")).toBe("true");
    
    act(() => {
      result.current.toggle();
    });
    
    expect(result.current.isCollapsed).toBe(false);
    expect(localStorage.getItem("admin-sidebar-collapsed")).toBe("false");
  });

  it("should listen for storage changes", () => {
    const { result } = renderHook(() => useAdminSidebarState());
    
    expect(result.current.isCollapsed).toBe(false);
    
    act(() => {
      // Simulate storage event from another tab
      const event = new StorageEvent("storage", {
        key: "admin-sidebar-collapsed",
        newValue: "true",
      });
      window.dispatchEvent(event);
    });
    
    expect(result.current.isCollapsed).toBe(true);
  });
});
