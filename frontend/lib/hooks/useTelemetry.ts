/**
 * React hook for telemetry in session pages
 */

import { useEffect, useRef } from "react";
import { TelemetryClient, createTelemetryClient, EventType } from "../telemetry/telemetryClient";

export function useTelemetry(sessionId: string | null, enabled: boolean = true) {
  const clientRef = useRef<TelemetryClient | null>(null);

  useEffect(() => {
    if (!sessionId || !enabled) {
      return;
    }

    // Create client
    clientRef.current = createTelemetryClient(sessionId);

    // Cleanup on unmount
    return () => {
      if (clientRef.current) {
        clientRef.current.stop();
        clientRef.current = null;
      }
    };
  }, [sessionId, enabled]);

  const track = (
    eventType: EventType,
    payload?: Record<string, unknown>,
    questionId?: string | null,
  ) => {
    if (clientRef.current) {
      clientRef.current.track(eventType, payload, questionId);
    }
  };

  const flush = async () => {
    if (clientRef.current) {
      await clientRef.current.flush();
    }
  };

  return { track, flush };
}
