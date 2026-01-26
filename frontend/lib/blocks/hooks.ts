/**
 * Hooks for block detail page data fetching.
 */

import { useEffect, useState } from "react";
import { syllabusAPI, onboardingAPI } from "@/lib/api";
import { Year, Block, Theme } from "@/lib/api";
import { logger } from "@/lib/logger";

interface UseBlockDataResult {
  block: Block | null;
  year: Year | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Fetch block data by blockId.
 * Since there's no direct "get block by id" endpoint, we:
 * 1. Load user's selected year (or default to first year)
 * 2. Load blocks for that year
 * 3. Find the matching block
 */
export function useBlockData(blockId: number): UseBlockDataResult {
  const [state, setState] = useState<UseBlockDataResult>({
    block: null,
    year: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadBlock() {
      try {
        // Load years
        const years = await syllabusAPI.getYears();
        if (years.length === 0) {
          throw new Error("No years available");
        }

        // Try to get user's selected year
        let selectedYear: Year | null = null;
        try {
          const profile = await onboardingAPI.getProfile();
          if (profile.selected_year) {
            const matchingYear = years.find((y) => y.name === profile.selected_year?.display_name);
            if (matchingYear) {
              selectedYear = matchingYear;
            }
          }
        } catch (err) {
          logger.warn("Failed to load profile, using first year:", err);
        }

        // Default to first year if no profile year
        if (!selectedYear) {
          selectedYear = years[0];
        }

        // Load blocks for selected year
        const blocks = await syllabusAPI.getBlocks(selectedYear.name);

        // Find the matching block
        const block = blocks.find((b) => b.id === blockId);

        if (!block) {
          // Try other years if not found
          for (const year of years) {
            if (year.id === selectedYear.id) continue;
            const yearBlocks = await syllabusAPI.getBlocks(year.name);
            const foundBlock = yearBlocks.find((b) => b.id === blockId);
            if (foundBlock) {
              if (cancelled) return;
              setState({
                block: foundBlock,
                year: year,
                loading: false,
                error: null,
              });
              return;
            }
          }
          throw new Error(`Block with ID ${blockId} not found`);
        }

        if (cancelled) return;

        setState({
          block,
          year: selectedYear,
          loading: false,
          error: null,
        });
      } catch (error) {
        if (cancelled) return;
        setState({
          block: null,
          year: null,
          loading: false,
          error: error instanceof Error ? error : new Error("Failed to load block"),
        });
      }
    }

    loadBlock();

    return () => {
      cancelled = true;
    };
  }, [blockId]);

  return state;
}

interface UseThemesResult {
  themes: Theme[];
  loading: boolean;
  error: Error | null;
}

/**
 * Fetch themes for a block.
 */
export function useThemes(blockId: number): UseThemesResult {
  const [state, setState] = useState<UseThemesResult>({
    themes: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadThemes() {
      try {
        const themes = await syllabusAPI.getThemes(blockId);
        if (cancelled) return;
        setState({ themes, loading: false, error: null });
      } catch (error) {
        if (cancelled) return;
        setState({
          themes: [],
          loading: false,
          error: error instanceof Error ? error : new Error("Failed to load themes"),
        });
      }
    }

    loadThemes();

    return () => {
      cancelled = true;
    };
  }, [blockId]);

  return state;
}

// Allowed blocks hooks removed - platform is now fully self-paced
// All blocks/themes are always available for practice
