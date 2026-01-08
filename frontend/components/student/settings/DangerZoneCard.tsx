"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertTriangle } from "lucide-react";

export function DangerZoneCard() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const handleReset = () => {
    // TODO: Implement when backend endpoint exists
    alert("Reset functionality not yet implemented. Please contact admin.");
  };

  return (
    <Card className="border-destructive">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-5 w-5" />
          Danger Zone
        </CardTitle>
        <CardDescription>Irreversible actions</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button
          variant="outline"
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full"
        >
          {isExpanded ? "Hide" : "Show"} reset progress options
        </Button>

        {isExpanded && (
          <div className="space-y-4 rounded-lg border border-destructive/50 bg-destructive/5 p-4">
            <div>
              <h4 className="font-medium">Reset practice data</h4>
              <p className="text-sm text-muted-foreground mt-1">
                This will reset your practice sessions and analytics. Syllabus access will remain
                unchanged.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-reset">
                Type <span className="font-mono font-bold">RESET</span> to confirm
              </Label>
              <Input
                id="confirm-reset"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="RESET"
                className="font-mono"
              />
            </div>

            <Button
              variant="destructive"
              onClick={handleReset}
              disabled={confirmText !== "RESET"}
            >
              Reset my practice data
            </Button>

            <p className="text-xs text-muted-foreground">
              If you need help, contact admin
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
