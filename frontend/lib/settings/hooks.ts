/**
 * Hooks for settings page data fetching.
 */

import { useEffect, useState } from "react";
import { syllabusAPI, onboardingAPI } from "@/lib/api";
import { Year, Block, UserProfile } from "@/lib/api";

interface UseYearsResult {
  years: Year[];
  loading: boolean;
  error: Error | null;
}

/**
 * Fetch all active years.
 */
export function useYears(): UseYearsResult {
  const [state, setState] = useState<UseYearsResult>({
    years: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadYears() {
      try {
        const years = await syllabusAPI.getYears();
        if (cancelled) return;
        setState({ years, loading: false, error: null });
      } catch (error) {
        if (cancelled) return;
        setState({
          years: [],
          loading: false,
          error: error instanceof Error ? error : new Error("Failed to load years"),
        });
      }
    }

    loadYears();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

interface UseBlocksForYearResult {
  blocks: Block[];
  loading: boolean;
  error: Error | null;
}

/**
 * Fetch blocks for a specific year.
 */
export function useBlocksForYear(yearName: string | null): UseBlocksForYearResult {
  const [state, setState] = useState<UseBlocksForYearResult>({
    blocks: [],
    loading: false,
    error: null,
  });

  useEffect(() => {
    if (!yearName) {
      setState({ blocks: [], loading: false, error: null });
      return;
    }

    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    async function loadBlocks() {
      try {
        const blocks = await syllabusAPI.getBlocks(yearName);
        if (cancelled) return;
        setState({ blocks, loading: false, error: null });
      } catch (error) {
        if (cancelled) return;
        setState({
          blocks: [],
          loading: false,
          error: error instanceof Error ? error : new Error("Failed to load blocks"),
        });
      }
    }

    loadBlocks();

    return () => {
      cancelled = true;
    };
  }, [yearName]);

  return state;
}

interface UseProfileResult {
  profile: UserProfile | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Fetch user profile.
 */
export function useProfile(): UseProfileResult {
  const [state, setState] = useState<UseProfileResult>({
    profile: null,
    loading: true,
    error: null,
    refetch: () => {},
  });

  const loadProfile = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const profile = await onboardingAPI.getProfile();
      setState({ profile, loading: false, error: null, refetch: loadProfile });
    } catch (error) {
      setState({
        profile: null,
        loading: false,
        error: error instanceof Error ? error : new Error("Failed to load profile"),
        refetch: loadProfile,
      });
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  return state;
}

// useAllowedBlocks hook removed - platform is now fully self-paced
