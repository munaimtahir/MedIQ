"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RotateCcw } from "lucide-react";

export default function RevisionPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Revision</h1>
        <p className="text-muted-foreground">Review your past sessions and mistakes</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Past Sessions</CardTitle>
          <CardDescription>Review your completed practice sessions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center text-muted-foreground">
            <RotateCcw className="mx-auto mb-4 h-12 w-12 opacity-50" />
            <p>No past sessions yet. Complete a practice session to see it here.</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Mistakes Review</CardTitle>
          <CardDescription>Questions you got wrong</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center text-muted-foreground">
            <p>No mistakes to review yet.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
