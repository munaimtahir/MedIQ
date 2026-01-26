"use client";

import Link from "next/link";
import { useRuntimeStatus } from "@/lib/admin/runtime/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, Settings } from "lucide-react";

export default function AdminSystemPage() {
  const { status, loading, error, refetch } = useRuntimeStatus();

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Runtime Control</h1>
          <p className="text-muted-foreground">Flags, profile, and module overrides</p>
        </div>
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Runtime Control</h1>
          <p className="text-muted-foreground">Flags, profile, and module overrides</p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>Failed to load runtime status: {error.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!status) return null;

  const { flags, active_profile, resolved, last_changed } = status;
  const examActive = flags?.EXAM_MODE?.enabled ?? false;
  const freezeActive = flags?.FREEZE_UPDATES?.enabled ?? false;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Runtime Control</h1>
          <p className="text-muted-foreground">Flags, profile, and module overrides</p>
        </div>
        <Link href="/admin/settings">
          <span className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted">
            <Settings className="h-4 w-4" />
            Settings (Exam Mode, Freeze)
          </span>
        </Link>
      </div>

      {(examActive || freezeActive) && (
        <Alert variant="destructive" className="border-l-4 border-l-destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {examActive && <span className="font-semibold">Exam Mode ACTIVE</span>}
            {examActive && freezeActive && " · "}
            {freezeActive && <span className="font-semibold">Freeze Updates ACTIVE</span>}
            {" — "}
            Heavy operations and learning state writes are blocked.
            <Link href="/admin/settings" className="ml-2 font-medium underline hover:no-underline">
              Manage
            </Link>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Flags</CardTitle>
            <CardDescription>EXAM_MODE and FREEZE_UPDATES</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span>Exam Mode</span>
              <Badge variant={examActive ? "destructive" : "secondary"}>{examActive ? "ACTIVE" : "INACTIVE"}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Freeze Updates</span>
              <Badge variant={freezeActive ? "destructive" : "secondary"}>{freezeActive ? "ACTIVE" : "INACTIVE"}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Toggle in <Link href="/admin/settings" className="underline">Settings → System</Link>.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Profile</CardTitle>
            <CardDescription>Runtime profile (primary / fallback / shadow)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{resolved?.profile ?? active_profile?.name ?? "—"}</Badge>
            </div>
            {last_changed && (
              <p className="mt-2 text-xs text-muted-foreground">
                Last change: {last_changed.action_type} at {last_changed.created_at ?? "—"}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Resolved Runtime</CardTitle>
          <CardDescription>Effective modules and feature toggles</CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="overflow-auto rounded-md border bg-muted/50 p-4 text-xs">
            {JSON.stringify(resolved ?? {}, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
