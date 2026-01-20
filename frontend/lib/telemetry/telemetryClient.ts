/**
 * Telemetry client for batching and sending behavioral events
 * 
 * IMPORTANT: All telemetry operations are best-effort and must NOT break the UI.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BATCH_SIZE = 10;
const FLUSH_INTERVAL = 12000; // 12 seconds
const MAX_RETRIES = 2;

export type EventType =
  | "SESSION_CREATED"
  | "QUESTION_VIEWED"
  | "NAVIGATE_NEXT"
  | "NAVIGATE_PREV"
  | "NAVIGATE_JUMP"
  | "ANSWER_SELECTED"
  | "ANSWER_CHANGED"
  | "MARK_FOR_REVIEW_TOGGLED"
  | "SESSION_SUBMITTED"
  | "SESSION_EXPIRED"
  | "REVIEW_OPENED"
  | "PAUSE_BLUR";

export interface TelemetryEvent {
  event_type: EventType;
  client_ts?: string;
  seq?: number;
  session_id: string;
  question_id?: string | null;
  payload?: Record<string, any>;
}

export interface TelemetryBatch {
  source: string;
  events: TelemetryEvent[];
}

export class TelemetryClient {
  private queue: TelemetryEvent[] = [];
  private seq = 0;
  private sessionId: string;
  private source: string;
  private flushTimer: NodeJS.Timeout | null = null;
  private isFlushing = false;

  constructor(sessionId: string, source: string = "web") {
    this.sessionId = sessionId;
    this.source = source;

    // Start flush timer
    this.startFlushTimer();

    // Flush on page unload (best-effort)
    if (typeof window !== "undefined") {
      window.addEventListener("beforeunload", () => this.flush());
      window.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
          this.flush();
        }
      });
    }
  }

  /**
   * Track an event (adds to queue)
   */
  track(
    eventType: EventType,
    payload?: Record<string, any>,
    questionId?: string | null
  ): void {
    try {
      this.seq += 1;

      const event: TelemetryEvent = {
        event_type: eventType,
        client_ts: new Date().toISOString(),
        seq: this.seq,
        session_id: this.sessionId,
        question_id: questionId,
        payload: payload || {},
      };

      this.queue.push(event);

      // Flush if batch size reached
      if (this.queue.length >= BATCH_SIZE) {
        this.flush();
      }
    } catch (err) {
      // Silent fail - telemetry must not break UI
      console.warn("Telemetry track failed:", err);
    }
  }

  /**
   * Force flush the queue
   */
  async flush(): Promise<void> {
    if (this.queue.length === 0 || this.isFlushing) {
      return;
    }

    this.isFlushing = true;
    const eventsToSend = [...this.queue];
    this.queue = []; // Clear queue immediately

    try {
      await this.sendBatch(eventsToSend);
    } catch (err) {
      // Silent fail - telemetry must not break UI
      console.warn("Telemetry flush failed:", err);
    } finally {
      this.isFlushing = false;
    }
  }

  /**
   * Send batch to backend with retry
   */
  private async sendBatch(
    events: TelemetryEvent[],
    retryCount = 0
  ): Promise<void> {
    if (events.length === 0) return;

    try {
      const batch: TelemetryBatch = {
        source: this.source,
        events,
      };

      const response = await fetch(`${API_BASE}/v1/telemetry/events`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(batch),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      
      // Log if any events were rejected (for debugging)
      if (result.rejected > 0) {
        console.debug(
          `Telemetry: ${result.accepted} accepted, ${result.rejected} rejected`,
          result.rejected_reasons_sample
        );
      }
    } catch (err) {
      // Retry with exponential backoff (up to MAX_RETRIES)
      if (retryCount < MAX_RETRIES) {
        const delay = Math.pow(2, retryCount) * 1000;
        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.sendBatch(events, retryCount + 1);
      }

      // Give up after max retries (silent fail)
      console.warn("Telemetry batch failed after retries:", err);
    }
  }

  /**
   * Start periodic flush timer
   */
  private startFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }

    this.flushTimer = setInterval(() => {
      this.flush();
    }, FLUSH_INTERVAL);
  }

  /**
   * Stop the client and flush remaining events
   */
  async stop(): Promise<void> {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }

    await this.flush();
  }
}

/**
 * Create a telemetry client instance
 */
export function createTelemetryClient(
  sessionId: string,
  source: string = "web"
): TelemetryClient {
  return new TelemetryClient(sessionId, source);
}
