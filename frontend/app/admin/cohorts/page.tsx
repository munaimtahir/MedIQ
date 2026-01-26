"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Info, BarChart3 } from "lucide-react";

export default function CohortsPage() {
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Cohort Analytics</h1>
        <p className="text-muted-foreground">Analytics dashboards for cohort comparisons</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Cohort Analytics Status
          </CardTitle>
          <CardDescription>Percentiles, comparisons, and rank simulation</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-2">
                <p className="font-medium">Cohort analytics not enabled yet.</p>
                <p className="text-sm">
                  Requires:
                </p>
                <ul className="text-sm list-disc list-inside space-y-1 ml-4">
                  <li>Warehouse mode set to &quot;active&quot;</li>
                  <li>Snowflake enabled and ready</li>
                  <li>Successful exports for required datasets (attempts, events, mastery)</li>
                  <li>Transform runs completed (curated, marts)</li>
                </ul>
                <p className="text-sm mt-2">
                  Once enabled, this page will show cohort analytics dashboards.
                </p>
              </div>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  );
}
