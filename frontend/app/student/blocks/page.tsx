"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { BlockCard } from "@/components/student/blocks/BlockCard";
import { syllabusAPI, onboardingAPI } from "@/lib/api";
import { Year, Block } from "@/lib/api";
import { AlertCircle } from "lucide-react";

export default function BlocksPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [years, setYears] = useState<Year[]>([]);
  const [selectedYearId, setSelectedYearId] = useState<number | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);

  // Load years and determine selected year
  useEffect(() => {
    loadInitialData();
  }, []);

  // Load blocks when year changes
  useEffect(() => {
    if (selectedYearId) {
      loadBlocks(selectedYearId);
    }
  }, [selectedYearId]);

  async function loadInitialData() {
    setLoading(true);
    setError(null);
    try {
      // Load years
      const yearsData = await syllabusAPI.getYears();
      setYears(yearsData);

      // Try to get user's selected year from profile
      try {
        const profile = await onboardingAPI.getProfile();
        if (profile.selected_year) {
          const profileYearName = profile.selected_year.display_name;
          console.log("[Blocks] User selected year from profile:", profileYearName);
          
          // Improved matching logic (same as dashboard)
          const matchingYear = yearsData.find((y) => {
            // Exact match
            if (y.name === profileYearName) return true;
            // Case-insensitive match
            if (y.name.toLowerCase() === profileYearName.toLowerCase()) return true;
            // Partial match
            if (y.name.toLowerCase().includes(profileYearName.toLowerCase()) || 
                profileYearName.toLowerCase().includes(y.name.toLowerCase())) return true;
            // Try matching by removing common suffixes
            const normalizedYear = y.name.toLowerCase().replace(/\s*(mbbs|year|yr)\s*/gi, "").trim();
            const normalizedProfile = profileYearName.toLowerCase().replace(/\s*(mbbs|year|yr)\s*/gi, "").trim();
            if (normalizedYear === normalizedProfile) return true;
            return false;
          });
          
          if (matchingYear) {
            console.log("[Blocks] Matched year:", matchingYear.name);
            setSelectedYearId(matchingYear.id);
            return;
          } else {
            console.warn("[Blocks] Could not match user's year, using first available");
          }
        }
      } catch (err) {
        console.warn("[Blocks] Failed to load profile, using first year:", err);
      }

      // Default to first year
      if (yearsData.length > 0) {
        setSelectedYearId(yearsData[0].id);
      }
    } catch (err) {
      console.error("Failed to load initial data:", err);
      setError(err instanceof Error ? err : new Error("Failed to load data"));
    } finally {
      setLoading(false);
    }
  }

  async function loadBlocks(yearId: number) {
    try {
      const year = years.find((y) => y.id === yearId);
      if (!year) return;

      const blocksData = await syllabusAPI.getBlocks(year.name);
      setBlocks(blocksData);
    } catch (err) {
      console.error("Failed to load blocks:", err);
      setError(err instanceof Error ? err : new Error("Failed to load blocks"));
    }
  }


  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <Skeleton className="h-64 w-full" />
        <div className="space-y-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Blocks</h1>
          <p className="text-muted-foreground">Curriculum overview for your selected year</p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <div>
                <p className="font-medium">Error loading blocks</p>
                <p className="text-sm text-muted-foreground">{error.message}</p>
              </div>
            </div>
            <Button onClick={loadInitialData} className="mt-4">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const selectedYear = years.find((y) => y.id === selectedYearId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Blocks</h1>
          <p className="text-muted-foreground">
            Browse and practice any block from {selectedYear?.name || "your selected year"}
          </p>
        </div>
        <Select
          value={selectedYearId?.toString() || ""}
          onValueChange={(value) => setSelectedYearId(Number(value))}
        >
          <SelectTrigger className="w-48">
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

      {/* Blocks List */}
      {blocks.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">
              No blocks available for this year. Complete onboarding to get started.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {blocks
            .sort((a, b) => a.order_no - b.order_no)
            .map((block) => (
              <BlockCard
                key={block.id}
                block={block}
                isAllowed={true}
              />
            ))}
        </div>
      )}
    </div>
  );
}
