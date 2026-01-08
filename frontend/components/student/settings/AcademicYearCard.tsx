"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
// Using browser confirm for now - can be replaced with proper dialog component later
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle } from "lucide-react";
import { Year } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";

interface AcademicYearCardProps {
  years: Year[];
  currentYearId: number | null;
  loading: boolean;
  error: Error | null;
  onYearChange: (yearId: number) => Promise<void>;
}

export function AcademicYearCard({
  years,
  currentYearId,
  loading,
  error,
  onYearChange,
}: AcademicYearCardProps) {
  const { toast } = useToast();
  const [selectedYearId, setSelectedYearId] = useState<string>(
    currentYearId?.toString() || ""
  );
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  // Update selected year when currentYearId changes
  useEffect(() => {
    setSelectedYearId(currentYearId?.toString() || "");
    setHasChanges(false);
  }, [currentYearId]);

  const handleYearSelect = (value: string) => {
    setSelectedYearId(value);
    setHasChanges(value !== (currentYearId?.toString() || ""));
  };

  const handleSave = async () => {
      const confirmed = window.confirm(
        "Change your academic year? This will update the blocks and themes shown in your navigation."
      );
    if (!confirmed) return;

    setSaving(true);
    try {
      await onYearChange(Number(selectedYearId));
      setHasChanges(false);
      toast({
        title: "Year updated",
        description: "Your academic year has been updated successfully.",
      });
    } catch (error) {
      console.error("Failed to update year:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to update academic year",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Academic year</CardTitle>
        <CardDescription>Select your current academic year</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span>{error.message}</span>
            </div>
          </div>
        )}
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium">Current academic year</label>
            <Select value={selectedYearId} onValueChange={handleYearSelect}>
              <SelectTrigger className="mt-2">
                <SelectValue placeholder="Select year" />
              </SelectTrigger>
              <SelectContent>
                {years.map((year) => (
                  <SelectItem key={year.id} value={year.id.toString()}>
                    {year.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1">
            <p className="text-sm text-muted-foreground">
              Changing your academic year updates available blocks and themes.
            </p>
          </div>
        </div>
        {hasChanges && (
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save year"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
