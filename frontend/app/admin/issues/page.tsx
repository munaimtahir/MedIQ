"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, Construction } from "lucide-react";

export default function IssuesPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <AlertCircle className="h-8 w-8" />
          <h1 className="text-3xl font-bold">Content Quality Issues</h1>
        </div>
        <p className="text-muted-foreground">Automated quality checks and issue tracking</p>
      </div>

      <Alert>
        <Construction className="h-4 w-4" />
        <AlertTitle>Coming Soon</AlertTitle>
        <AlertDescription>
          The Content Quality Issues feature is currently under development. This page will soon
          provide automated quality checks including:
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Planned Features</CardTitle>
          <CardDescription>What this page will offer when completed</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground">•</span>
              <span>
                <strong>Missing Tags:</strong> Questions without year, block, or theme assignments
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground">•</span>
              <span>
                <strong>Missing Source:</strong> Questions without source book or page references
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground">•</span>
              <span>
                <strong>Invalid Option Count:</strong> Questions with fewer or more than 5 options
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground">•</span>
              <span>
                <strong>Duplicate Detection:</strong> Questions with similar or identical stems
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground">•</span>
              <span>
                <strong>Missing Explanation:</strong> Questions without detailed explanations
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground">•</span>
              <span>
                <strong>Incomplete Metadata:</strong> Questions missing cognitive level or
                difficulty
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground">•</span>
              <span>
                <strong>Orphaned Questions:</strong> Questions in deleted or inactive syllabus items
              </span>
            </li>
          </ul>
        </CardContent>
      </Card>

      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-base">Why Quality Checks Matter</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>
            Automated quality checks help maintain a high-quality question bank by identifying
            potential issues early. Regular reviews of flagged items ensure students receive
            well-structured, properly tagged, and thoroughly explained questions that enhance their
            learning experience.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
