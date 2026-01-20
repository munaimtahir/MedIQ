/**
 * Countdown hook for timed sessions
 */

import { useState, useEffect, useRef } from "react";

export interface CountdownState {
  remainingSeconds: number;
  isExpired: boolean;
  formattedTime: string;
  isWarning: boolean; // true if < 5 minutes remaining
}

/**
 * Hook to manage countdown timer
 * @param expiresAt ISO timestamp when session expires
 * @param onExpire Callback when timer reaches 0
 */
export function useCountdown(
  expiresAt: string | null,
  onExpire?: () => void
): CountdownState {
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [isExpired, setIsExpired] = useState(false);
  const onExpireRef = useRef(onExpire);

  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);

  useEffect(() => {
    if (!expiresAt) {
      setRemainingSeconds(0);
      setIsExpired(false);
      return;
    }

    const calculateRemaining = () => {
      const now = new Date().getTime();
      const expires = new Date(expiresAt).getTime();
      const diff = Math.max(0, Math.floor((expires - now) / 1000));
      return diff;
    };

    // Initial calculation
    const initial = calculateRemaining();
    setRemainingSeconds(initial);
    setIsExpired(initial === 0);

    if (initial === 0 && onExpireRef.current) {
      onExpireRef.current();
    }

    // Update every second
    const interval = setInterval(() => {
      const remaining = calculateRemaining();
      setRemainingSeconds(remaining);

      if (remaining === 0 && !isExpired) {
        setIsExpired(true);
        if (onExpireRef.current) {
          onExpireRef.current();
        }
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, isExpired]);

  const hours = Math.floor(remainingSeconds / 3600);
  const minutes = Math.floor((remainingSeconds % 3600) / 60);
  const seconds = remainingSeconds % 60;

  const formattedTime =
    hours > 0
      ? `${hours}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
      : `${minutes}:${seconds.toString().padStart(2, "0")}`;

  const isWarning = remainingSeconds > 0 && remainingSeconds < 300; // 5 minutes

  return {
    remainingSeconds,
    isExpired,
    formattedTime,
    isWarning,
  };
}
