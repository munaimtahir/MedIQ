/**
 * Production-safe logger that conditionally logs based on environment
 */

const isDev = process.env.NODE_ENV === "development";

export const logger = {
  log: (...args: unknown[]) => {
    if (isDev) console.log(...args);
  },
  warn: (...args: unknown[]) => {
    if (isDev) console.warn(...args);
  },
  error: (...args: unknown[]) => {
    // Always log errors, but send to monitoring in production
    console.error(...args);
    if (!isDev) {
      // TODO: Send to Sentry/LogRocket/monitoring service
      // Example: Sentry.captureException(args[0]);
    }
  },
  debug: (...args: unknown[]) => {
    if (isDev) console.debug(...args);
  },
};
