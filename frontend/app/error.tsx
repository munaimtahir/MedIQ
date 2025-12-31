"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/status/ErrorState";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log error to error reporting service
    console.error("Application error:", error);
  }, [error]);

  return (
    <ErrorState
      variant="page"
      title="Something went wrong"
      description="An unexpected error occurred. Please try again."
      errorCode={error.digest}
      actionLabel="Try again"
      onAction={reset}
      showSupportHint={true}
    />
  );
}

