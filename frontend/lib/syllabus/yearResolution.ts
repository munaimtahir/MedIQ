/**
 * Unified year resolution utility.
 * Provides consistent logic for resolving user's selected year across the app.
 */

import { Year } from "@/lib/api";
import { UserProfile } from "@/lib/api";

export interface YearResolutionResult {
  year: Year | null;
  yearId: number | null;
  yearName: string | null;
  source: "query" | "profile" | "default" | "none";
}

/**
 * Resolve the user's selected year with fallback logic.
 *
 * Priority:
 * 1. Query parameter (year_id)
 * 2. User profile (selected_year)
 * 3. First active year from years list
 * 4. null if no years available
 *
 * @param years - List of available years
 * @param profile - User profile (optional)
 * @param yearIdFromQuery - Year ID from query parameter (optional)
 * @returns Resolved year information
 */
export function resolveUserYear(
  years: Year[],
  profile: UserProfile | null = null,
  yearIdFromQuery: number | null = null
): YearResolutionResult {
  // Priority 1: Query parameter
  if (yearIdFromQuery !== null) {
    const year = years.find((y) => y.id === yearIdFromQuery);
    if (year) {
      return {
        year,
        yearId: year.id,
        yearName: year.name,
        source: "query",
      };
    }
  }

  // Priority 2: User profile
  if (profile?.selected_year) {
    const profileYearName = profile.selected_year.display_name;
    // Try exact match first
    let year = years.find((y) => y.name === profileYearName);
    // Try case-insensitive match
    if (!year) {
      year = years.find(
        (y) => y.name.toLowerCase() === profileYearName.toLowerCase()
      );
    }
    // Try normalized match (trim whitespace)
    if (!year) {
      const normalizedProfileName = profileYearName.trim();
      year = years.find(
        (y) => y.name.trim().toLowerCase() === normalizedProfileName.toLowerCase()
      );
    }

    if (year) {
      return {
        year,
        yearId: year.id,
        yearName: year.name,
        source: "profile",
      };
    }
  }

  // Priority 3: Default to first year
  if (years.length > 0) {
    const firstYear = years[0];
    return {
      year: firstYear,
      yearId: firstYear.id,
      yearName: firstYear.name,
      source: "default",
    };
  }

  // Priority 4: No years available
  return {
    year: null,
    yearId: null,
    yearName: null,
    source: "none",
  };
}

/**
 * Find a year by ID.
 */
export function findYearById(years: Year[], yearId: number): Year | null {
  return years.find((y) => y.id === yearId) || null;
}

/**
 * Find a year by name (with fallback matching).
 */
export function findYearByName(years: Year[], yearName: string): Year | null {
  // Exact match
  let year = years.find((y) => y.name === yearName);
  if (year) return year;

  // Case-insensitive match
  year = years.find((y) => y.name.toLowerCase() === yearName.toLowerCase());
  if (year) return year;

  // Normalized match
  const normalized = yearName.trim().toLowerCase();
  year = years.find((y) => y.name.trim().toLowerCase() === normalized);
  return year || null;
}
