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
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { syllabusAPI } from "@/lib/api";
import { Year } from "@/lib/api";

interface SyllabusShortcutsCardProps {
  loading?: boolean;
}

export function SyllabusShortcutsCard({ loading }: SyllabusShortcutsCardProps) {
  const router = useRouter();
  const [years, setYears] = useState<Year[]>([]);
  const [selectedYearId, setSelectedYearId] = useState<number | null>(null);
  const [blocksCount, setBlocksCount] = useState<number | null>(null);
  const [themesCount, setThemesCount] = useState<number | null>(null);
  const [loadingCounts, setLoadingCounts] = useState(false);

  useEffect(() => {
    loadYears();
  }, []);

  useEffect(() => {
    if (selectedYearId) {
      loadCounts(selectedYearId);
    }
  }, [selectedYearId]);

  async function loadYears() {
    try {
      const data = await syllabusAPI.getYears();
      setYears(data);
      if (data.length > 0) {
        setSelectedYearId(data[0].id);
      }
    } catch (error) {
      console.error("Failed to load years:", error);
    }
  }

  async function loadCounts(yearId: number) {
    setLoadingCounts(true);
    try {
      const year = years.find((y) => y.id === yearId);
      if (!year) return;

      const blocks = await syllabusAPI.getBlocks(year.name);
      setBlocksCount(blocks.length);

      // Count themes across all blocks
      let totalThemes = 0;
      for (const block of blocks) {
        try {
          const themes = await syllabusAPI.getThemes(block.id);
          totalThemes += themes.length;
        } catch (error) {
          console.error(`Failed to load themes for block ${block.id}:`, error);
        }
      }
      setThemesCount(totalThemes);
    } catch (error) {
      console.error("Failed to load counts:", error);
    } finally {
      setLoadingCounts(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-64 mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  const selectedYear = years.find((y) => y.id === selectedYearId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Syllabus Shortcuts</CardTitle>
        <CardDescription>Quick access to syllabus management</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">Select Year</label>
          <Select
            value={selectedYearId?.toString() || ""}
            onValueChange={(value) => setSelectedYearId(Number(value))}
          >
            <SelectTrigger>
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

        {selectedYear && (
          <div className="space-y-2 text-sm">
            {loadingCounts ? (
              <>
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div>
                  <span className="text-muted-foreground">Blocks: </span>
                  <span className="font-medium">{blocksCount ?? "--"}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Themes: </span>
                  <span className="font-medium">{themesCount ?? "--"}</span>
                </div>
              </>
            )}
          </div>
        )}

        <div className="flex flex-col gap-2 pt-2">
          <Button
            variant="default"
            onClick={() => router.push("/admin/syllabus")}
            className="w-full"
          >
            Open Syllabus Manager
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
