/**
 * Hooks for admin syllabus data fetching and operations.
 */

import { useState, useEffect, useCallback } from "react";
import { adminSyllabusAPI, YearAdmin, BlockAdmin, ThemeAdmin } from "@/lib/api";
import { notify } from "@/lib/notify";

// Years hooks
export function useAdminYears() {
  const [years, setYears] = useState<YearAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadYears = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminSyllabusAPI.getYears();
      setYears(data.sort((a, b) => a.order_no - b.order_no));
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load years");
      setError(error);
      notify.error("Failed to load years", error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadYears();
  }, [loadYears]);

  return { years, loading, error, refetch: loadYears };
}

// Blocks hooks
export function useAdminBlocks(yearId: number | null) {
  const [blocks, setBlocks] = useState<BlockAdmin[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadBlocks = useCallback(async () => {
    // Validate yearId - must be a valid positive integer
    // Early return if yearId is invalid - don't make API call
    if (
      yearId === null ||
      yearId === undefined ||
      yearId === 0 ||
      typeof yearId !== "number" ||
      isNaN(yearId) ||
      !Number.isInteger(yearId) ||
      yearId <= 0
    ) {
      // Clear blocks and reset state if yearId is invalid
      setBlocks([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    // Only make API call if yearId is valid
    setLoading(true);
    setError(null);
    try {
      const data = await adminSyllabusAPI.getBlocks(yearId);
      setBlocks(data.sort((a, b) => a.order_no - b.order_no));
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load blocks");
      setError(error);
      // Only show error notification if it's not a validation error
      if (!error.message.includes("required") && !error.message.includes("INVALID")) {
        notify.error("Failed to load blocks", error.message);
      }
    } finally {
      setLoading(false);
    }
  }, [yearId]);

  useEffect(() => {
    // Only call loadBlocks if yearId is valid
    if (
      yearId !== null &&
      yearId !== undefined &&
      yearId !== 0 &&
      typeof yearId === "number" &&
      !isNaN(yearId) &&
      Number.isInteger(yearId) &&
      yearId > 0
    ) {
      loadBlocks();
    } else {
      // Reset state if yearId is invalid
      setBlocks([]);
      setLoading(false);
      setError(null);
    }
  }, [yearId, loadBlocks]);

  return { blocks, loading, error, refetch: loadBlocks };
}

// Themes hooks
export function useAdminThemes(blockId: number | null) {
  const [themes, setThemes] = useState<ThemeAdmin[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadThemes = useCallback(async () => {
    // Validate blockId - must be a valid positive integer
    // Early return if blockId is invalid - don't make API call
    if (
      blockId === null ||
      blockId === undefined ||
      blockId === 0 ||
      typeof blockId !== "number" ||
      isNaN(blockId) ||
      !Number.isInteger(blockId) ||
      blockId <= 0
    ) {
      // Clear themes and reset state if blockId is invalid
      setThemes([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    // Only make API call if blockId is valid
    setLoading(true);
    setError(null);
    try {
      const data = await adminSyllabusAPI.getThemes(blockId);
      setThemes(data.sort((a, b) => a.order_no - b.order_no));
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to load themes");
      setError(error);
      // Only show error notification if it's not a validation error
      if (!error.message.includes("required") && !error.message.includes("INVALID")) {
        notify.error("Failed to load themes", error.message);
      }
    } finally {
      setLoading(false);
    }
  }, [blockId]);

  useEffect(() => {
    // Only call loadThemes if blockId is valid
    if (
      blockId !== null &&
      blockId !== undefined &&
      blockId !== 0 &&
      typeof blockId === "number" &&
      !isNaN(blockId) &&
      Number.isInteger(blockId) &&
      blockId > 0
    ) {
      loadThemes();
    } else {
      // Reset state if blockId is invalid
      setThemes([]);
      setLoading(false);
      setError(null);
    }
  }, [blockId, loadThemes]);

  return { themes, loading, error, refetch: loadThemes };
}

// Reorder hooks
export function useReorderYears() {
  const [reordering, setReordering] = useState(false);

  const reorderYears = useCallback(async (orderedIds: number[]) => {
    setReordering(true);
    try {
      // Note: Backend may not have a years reorder endpoint - using update for now
      // If backend has /years/reorder, use that instead
      await Promise.all(
        orderedIds.map((id, index) =>
          adminSyllabusAPI.updateYear(id, { order_no: index + 1 })
        )
      );
      notify.success("Years reordered", "Order updated successfully");
      return true;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to reorder years");
      notify.error("Failed to reorder", error.message);
      return false;
    } finally {
      setReordering(false);
    }
  }, []);

  return { reorderYears, reordering };
}

export function useReorderBlocks() {
  const [reordering, setReordering] = useState(false);

  const reorderBlocks = useCallback(async (yearId: number, orderedIds: number[]) => {
    setReordering(true);
    try {
      await adminSyllabusAPI.reorderBlocks(yearId, orderedIds);
      notify.success("Blocks reordered", "Order updated successfully");
      return true;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to reorder blocks");
      notify.error("Failed to reorder", error.message);
      return false;
    } finally {
      setReordering(false);
    }
  }, []);

  return { reorderBlocks, reordering };
}

export function useReorderThemes() {
  const [reordering, setReordering] = useState(false);

  const reorderThemes = useCallback(async (blockId: number, orderedIds: number[]) => {
    setReordering(true);
    try {
      await adminSyllabusAPI.reorderThemes(blockId, orderedIds);
      notify.success("Themes reordered", "Order updated successfully");
      return true;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to reorder themes");
      notify.error("Failed to reorder", error.message);
      return false;
    } finally {
      setReordering(false);
    }
  }, []);

  return { reorderThemes, reordering };
}

// CRUD hooks
export function useCrudYear() {
  const createYear = useCallback(async (data: { name: string; order_no: number; is_active?: boolean }) => {
    try {
      const year = await adminSyllabusAPI.createYear(data);
      notify.success("Year created", `Created "${year.name}"`);
      return year;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to create year");
      notify.error("Failed to create year", error.message);
      throw error;
    }
  }, []);

  const updateYear = useCallback(async (id: number, data: Partial<YearAdmin>) => {
    try {
      const year = await adminSyllabusAPI.updateYear(id, data);
      notify.success("Year updated", `Updated "${year.name}"`);
      return year;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update year");
      notify.error("Failed to update year", error.message);
      throw error;
    }
  }, []);

  const toggleYear = useCallback(async (id: number, isActive: boolean) => {
    try {
      const year = isActive
        ? await adminSyllabusAPI.enableYear(id)
        : await adminSyllabusAPI.disableYear(id);
      notify.success(isActive ? "Year enabled" : "Year disabled");
      return year;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update year");
      notify.error("Failed to update year", error.message);
      throw error;
    }
  }, []);

  return { createYear, updateYear, toggleYear };
}

export function useCrudBlock() {
  const createBlock = useCallback(async (data: { year_id: number; code: string; name: string; order_no: number; is_active?: boolean }) => {
    try {
      const block = await adminSyllabusAPI.createBlock(data);
      notify.success("Block created", `Created "${block.code}"`);
      return block;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to create block");
      notify.error("Failed to create block", error.message);
      throw error;
    }
  }, []);

  const updateBlock = useCallback(async (id: number, data: Partial<BlockAdmin>) => {
    try {
      const block = await adminSyllabusAPI.updateBlock(id, data);
      notify.success("Block updated", `Updated "${block.code}"`);
      return block;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update block");
      notify.error("Failed to update block", error.message);
      throw error;
    }
  }, []);

  const toggleBlock = useCallback(async (id: number, isActive: boolean) => {
    try {
      const block = isActive
        ? await adminSyllabusAPI.enableBlock(id)
        : await adminSyllabusAPI.disableBlock(id);
      notify.success(isActive ? "Block enabled" : "Block disabled");
      return block;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update block");
      notify.error("Failed to update block", error.message);
      throw error;
    }
  }, []);

  return { createBlock, updateBlock, toggleBlock };
}

export function useCrudTheme() {
  const createTheme = useCallback(async (data: { block_id: number; title: string; order_no: number; description?: string; is_active?: boolean }) => {
    try {
      const theme = await adminSyllabusAPI.createTheme(data);
      notify.success("Theme created", `Created "${theme.title}"`);
      return theme;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to create theme");
      notify.error("Failed to create theme", error.message);
      throw error;
    }
  }, []);

  const updateTheme = useCallback(async (id: number, data: Partial<ThemeAdmin>) => {
    try {
      const theme = await adminSyllabusAPI.updateTheme(id, data);
      notify.success("Theme updated", `Updated "${theme.title}"`);
      return theme;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update theme");
      notify.error("Failed to update theme", error.message);
      throw error;
    }
  }, []);

  const toggleTheme = useCallback(async (id: number, isActive: boolean) => {
    try {
      const theme = isActive
        ? await adminSyllabusAPI.enableTheme(id)
        : await adminSyllabusAPI.disableTheme(id);
      notify.success(isActive ? "Theme enabled" : "Theme disabled");
      return theme;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update theme");
      notify.error("Failed to update theme", error.message);
      throw error;
    }
  }, []);

  return { createTheme, updateTheme, toggleTheme };
}

// CSV Import hook
export function useCsvImport() {
  const [importing, setImporting] = useState(false);

  const importCsv = useCallback(async (
    type: "years" | "blocks" | "themes",
    file: File,
    dryRun: boolean = true,
    autoCreate: boolean = false
  ) => {
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const params = new URLSearchParams();
      if (dryRun) params.set("dry_run", "true");
      if (autoCreate) params.set("auto_create", "true");

      const response = await fetch(`/api/admin/syllabus/import/${type}?${params.toString()}`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || "Failed to import CSV");
      }

      const result = await response.json();
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to import CSV");
      notify.error("Import failed", error.message);
      throw error;
    } finally {
      setImporting(false);
    }
  }, []);

  return { importCsv, importing };
}
