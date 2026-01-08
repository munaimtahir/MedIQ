"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SystemInfo } from "@/lib/admin/settings/hooks";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, XCircle } from "lucide-react";

interface SystemInfoProps {
  info: SystemInfo | null;
  loading: boolean;
}

export function SystemInfo({ info, loading }: SystemInfoProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="mt-2 h-4 w-64" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!info) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Information</CardTitle>
          <CardDescription>Platform system details</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Unable to load system information</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Information</CardTitle>
        <CardDescription>Platform system details (read-only)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Environment</span>
          <Badge variant="secondary">{info.environment || "—"}</Badge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">API Version</span>
          <span className="text-sm text-muted-foreground">{info.api_version || "—"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Backend Version</span>
          <span className="text-sm text-muted-foreground">{info.backend_version || "—"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Database</span>
          <div className="flex items-center gap-2">
            {info.db_connected ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <span className="text-sm text-muted-foreground">Connected</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-red-600" />
                <span className="text-sm text-muted-foreground">Disconnected</span>
              </>
            )}
          </div>
        </div>
        {info.redis_connected !== null && (
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Redis</span>
            <div className="flex items-center gap-2">
              {info.redis_connected ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <span className="text-sm text-muted-foreground">Connected</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="text-sm text-muted-foreground">Disconnected</span>
                </>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
