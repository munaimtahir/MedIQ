"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";

interface UsersErrorProps {
  message: string;
  onRetry: () => void;
}

export function UsersError({ message, onRetry }: UsersErrorProps) {
  return (
    <Card className="border-destructive">
      <CardContent className="pt-6">
        <div className="flex items-center gap-2 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <div className="flex-1">
            <p className="font-medium">Error</p>
            <p className="text-sm text-muted-foreground">{message}</p>
          </div>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
