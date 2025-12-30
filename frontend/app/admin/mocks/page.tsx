"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText } from "lucide-react";

export default function MocksPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Mock Exams</h1>
        <p className="text-muted-foreground">Manage mock exam configurations</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mock Exams</CardTitle>
          <CardDescription>Create and manage mock exam sets</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center text-muted-foreground">
            <FileText className="mx-auto mb-4 h-12 w-12 opacity-50" />
            <p>No mock exams configured</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
