"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Block, Theme } from "@/lib/api";
import { BookOpen } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { syllabusAPI } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

interface BrowseSyllabusCardProps {
  blocks: Block[];
  themesByBlock: Record<number, Theme[]>;
  loading?: boolean;
  error?: Error | null;
}

export function BrowseSyllabusCard({
  blocks,
  themesByBlock,
  loading,
  error,
}: BrowseSyllabusCardProps) {
  const router = useRouter();
  const [selectedBlockId, setSelectedBlockId] = useState<number | null>(null);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loadingThemes, setLoadingThemes] = useState(false);
  const [recentThemes] = useState<Theme[]>([]); // Mock for now

  // Initialize selectedBlockId when blocks are available
  useEffect(() => {
    if (blocks.length > 0) {
      // If no block selected or selected block no longer exists, select first block
      if (!selectedBlockId || !blocks.find(b => b.id === selectedBlockId)) {
        setSelectedBlockId(blocks[0].id);
      }
    } else {
      // Reset if blocks become empty
      setSelectedBlockId(null);
      setThemes([]);
    }
  }, [blocks, selectedBlockId]);

  useEffect(() => {
    if (selectedBlockId) {
      // Check if themes already loaded
      if (themesByBlock[selectedBlockId]) {
        setThemes(themesByBlock[selectedBlockId]);
      } else {
        // Load themes for selected block
        setLoadingThemes(true);
        syllabusAPI
          .getThemes(selectedBlockId)
          .then(setThemes)
          .catch((err) => {
            console.warn("Failed to load themes:", err);
            setThemes([]);
          })
          .finally(() => setLoadingThemes(false));
      }
    } else {
      setThemes([]);
    }
  }, [selectedBlockId]); // Remove themesByBlock from deps to avoid infinite loops

  if (loading) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || blocks.length === 0) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle>Browse Syllabus</CardTitle>
          <CardDescription>Jump to blocks and themes</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {error ? "Unable to load syllabus." : "No blocks available."}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="col-span-full md:col-span-1">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Browse Syllabus
        </CardTitle>
        <CardDescription>Jump to blocks and themes</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Jump to Block</label>
          <Select
            value={selectedBlockId?.toString() || ""}
            onValueChange={(value) => setSelectedBlockId(Number(value))}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a block" />
            </SelectTrigger>
            <SelectContent>
              {blocks.map((block) => (
                <SelectItem key={block.id} value={block.id.toString()}>
                  {block.name} ({block.code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedBlockId && (
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => router.push(`/student/blocks/${selectedBlockId}`)}
            >
              <BookOpen className="mr-2 h-4 w-4" />
              Open Block
            </Button>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Jump to Theme</label>
          {loadingThemes ? (
            <Skeleton className="h-10 w-full" />
          ) : (
            <>
              <Select
                value=""
                onValueChange={(value) => {
                  const themeId = Number(value);
                  const blockId = selectedBlockId || blocks[0].id;
                  router.push(`/student/blocks/${blockId}/themes/${themeId}`);
                }}
                disabled={!selectedBlockId || themes.length === 0}
              >
                <SelectTrigger>
                  <SelectValue placeholder={themes.length === 0 ? "No themes" : "Select a theme"} />
                </SelectTrigger>
                <SelectContent>
                  {themes.map((theme) => (
                    <SelectItem key={theme.id} value={theme.id.toString()}>
                      {theme.name || `Theme ${theme.id}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
        </div>

        {recentThemes.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Recently Visited</label>
            <div className="flex flex-wrap gap-2">
              {recentThemes.map((theme) => (
                <Badge
                  key={theme.id}
                  variant="secondary"
                  className="cursor-pointer"
                  onClick={() => {
                    const blockId = selectedBlockId || blocks[0].id;
                    router.push(`/student/blocks/${blockId}/themes/${theme.id}`);
                  }}
                >
                  {theme.title}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
