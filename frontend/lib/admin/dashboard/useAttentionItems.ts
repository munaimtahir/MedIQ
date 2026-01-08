/**
 * Hook to compute attention items from syllabus data.
 */

import { useEffect, useState } from "react";
import { adminSyllabusAPI } from "@/lib/api";
import { BlockAdmin, ThemeAdmin } from "@/lib/api";
import { AttentionItem, computeAttentionItems } from "./attentionRules";

interface UseAttentionItemsResult {
  items: AttentionItem[];
  loading: boolean;
  error: Error | null;
}

export function useAttentionItems(): UseAttentionItemsResult {
  const [state, setState] = useState<UseAttentionItemsResult>({
    items: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
    loadAttentionItems();
  }, []);

  async function loadAttentionItems() {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      // Load all syllabus data
      const years = await adminSyllabusAPI.getYears();

      // Load blocks for all years
      const allBlocks: BlockAdmin[] = [];
      for (const year of years) {
        try {
          const blocks = await adminSyllabusAPI.getBlocks(year.id);
          allBlocks.push(...blocks);
        } catch (error) {
          console.error(`Failed to load blocks for year ${year.id}:`, error);
        }
      }

      // Load themes for all blocks
      const allThemes: ThemeAdmin[] = [];
      for (const block of allBlocks) {
        try {
          const themes = await adminSyllabusAPI.getThemes(block.id);
          allThemes.push(...themes);
        } catch (error) {
          console.error(`Failed to load themes for block ${block.id}:`, error);
        }
      }

      // Compute attention items
      const items = computeAttentionItems(years, allBlocks, allThemes);

      setState({
        items,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState({
        items: [],
        loading: false,
        error: error instanceof Error ? error : new Error("Failed to load attention items"),
      });
    }
  }

  return state;
}
