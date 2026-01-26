/**
 * Scroll position preservation utilities
 */

/**
 * Generate a hash from search params for storage key
 */
export function hashSearchParams(params: URLSearchParams): string {
  // Sort params for deterministic hashing
  const sorted = Array.from(params.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join("&");
  
  // Simple hash (for small strings, this is fine)
  let hash = 0;
  for (let i = 0; i < sorted.length; i++) {
    const char = sorted.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Save scroll position
 */
export function saveScrollPosition(params: URLSearchParams, scrollY: number): void {
  try {
    const key = `admin_questions_scroll:${hashSearchParams(params)}`;
    sessionStorage.setItem(key, scrollY.toString());
  } catch (e) {
    // Ignore storage errors (private browsing, etc.)
    console.warn("Failed to save scroll position:", e);
  }
}

/**
 * Restore scroll position
 */
export function restoreScrollPosition(params: URLSearchParams): number | null {
  try {
    const key = `admin_questions_scroll:${hashSearchParams(params)}`;
    const saved = sessionStorage.getItem(key);
    if (saved) {
      const scrollY = parseInt(saved, 10);
      if (!isNaN(scrollY)) {
        return scrollY;
      }
    }
  } catch (e) {
    console.warn("Failed to restore scroll position:", e);
  }
  return null;
}

/**
 * Save last opened question ID
 */
export function saveLastOpenedQuestion(params: URLSearchParams, questionId: string): void {
  try {
    const key = `admin_questions_last_opened:${hashSearchParams(params)}`;
    sessionStorage.setItem(key, questionId);
  } catch (e) {
    console.warn("Failed to save last opened question:", e);
  }
}

/**
 * Get last opened question ID
 */
export function getLastOpenedQuestion(params: URLSearchParams): string | null {
  try {
    const key = `admin_questions_last_opened:${hashSearchParams(params)}`;
    return sessionStorage.getItem(key);
  } catch (e) {
    console.warn("Failed to get last opened question:", e);
    return null;
  }
}
