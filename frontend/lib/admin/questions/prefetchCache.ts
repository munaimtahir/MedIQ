/**
 * Simple prefetch cache for question editor data
 * Limits prefetch requests to prevent spam
 */

interface PrefetchEntry {
  timestamp: number;
  promise: Promise<unknown>;
}

class PrefetchCache {
  private cache = new Map<string, PrefetchEntry>();
  private recentHovers: Array<{ questionId: string; timestamp: number }> = [];
  private readonly MAX_RECENT_HOVERS = 5;
  private readonly HOVER_WINDOW_MS = 10000; // 10 seconds
  private readonly CACHE_TTL_MS = 60000; // 1 minute

  /**
   * Check if we should prefetch (rate limiting)
   */
  shouldPrefetch(questionId: string): boolean {
    const now = Date.now();
    
    // Clean old hovers
    this.recentHovers = this.recentHovers.filter(
      (h) => now - h.timestamp < this.HOVER_WINDOW_MS,
    );

    // Check if we've exceeded the limit
    if (this.recentHovers.length >= this.MAX_RECENT_HOVERS) {
      return false;
    }

    // Check if already in cache and not stale
    const cached = this.cache.get(questionId);
    if (cached && now - cached.timestamp < this.CACHE_TTL_MS) {
      return false;
    }

    return true;
  }

  /**
   * Record a hover and return if prefetch should proceed
   */
  recordHover(questionId: string): boolean {
    if (!this.shouldPrefetch(questionId)) {
      return false;
    }

    const now = Date.now();
    this.recentHovers.push({ questionId, timestamp: now });
    return true;
  }

  /**
   * Store a prefetch promise
   */
  set(questionId: string, promise: Promise<unknown>): void {
    this.cache.set(questionId, {
      timestamp: Date.now(),
      promise,
    });
  }

  /**
   * Get cached promise (if exists and not stale)
   */
  get(questionId: string): Promise<unknown> | null {
    const cached = this.cache.get(questionId);
    if (!cached) return null;

    const now = Date.now();
    if (now - cached.timestamp > this.CACHE_TTL_MS) {
      this.cache.delete(questionId);
      return null;
    }

    return cached.promise;
  }

  /**
   * Clear cache
   */
  clear(): void {
    this.cache.clear();
    this.recentHovers = [];
  }
}

export const prefetchCache = new PrefetchCache();
