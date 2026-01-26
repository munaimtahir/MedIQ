"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";
import { useFreezeUpdates } from "@/lib/admin/settings/hooks";
import Link from "next/link";

export function FreezeUpdatesBanner() {
  const { state, loading } = useFreezeUpdates();
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (!loading && state?.enabled) {
      setIsVisible(true);
    } else {
      setIsVisible(false);
    }
  }, [state, loading]);

  if (!isVisible || !state?.enabled) {
    return null;
  }

  return (
    <Alert variant="destructive" className="mb-4 border-l-4 border-l-destructive">
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription className="flex items-center justify-between">
        <span>
          <strong>Freeze Updates ACTIVE</strong> — Learning state mutations are blocked. Session answer/submit
          will return 423.
        </span>
        <Link
          href="/admin/settings"
          className="ml-4 text-sm font-medium underline hover:no-underline"
        >
          Manage
        </Link>
      </AlertDescription>
    </Alert>
  );
}
