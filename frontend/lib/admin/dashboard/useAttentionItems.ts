/**
 * Hook to compute attention items from syllabus data.
 */

import { useEffect, useState } from "react";
import { syllabusAPI } from "@/lib/api";
import { Year, Block, Theme } from "@/lib/api";
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
      const years = await syllabusAPI.getYears();
      
      // Load blocks for all years
      const allBlocks: Block[] = [];
      for (const year of years) {
        try {
          const blocks = await syllabusAPI.getBlocks(year.name);
          allBlocks.push(...blocks);
        } catch (error) {
          console.error(`Failed to load blocks for year ${year.name}:`, error);
        }
      }

      // Load themes for all blocks
      const allThemes: Theme[] = [];
      for (const block of allBlocks) {
        try {
          const themes = await syllabusAPI.getThemes(block.id);
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
