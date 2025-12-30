"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export default function IssuesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Issues</h1>
        <p className="text-muted-foreground">Reported issues and bugs</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Reported Issues</CardTitle>
          <CardDescription>User-reported problems</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center text-muted-foreground">
            <AlertCircle className="mx-auto mb-4 h-12 w-12 opacity-50" />
            <p>No issues reported</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
