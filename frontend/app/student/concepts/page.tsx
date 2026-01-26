"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import { studentGraphAPI, type ConceptNode } from "@/lib/api/studentGraph";
import { syllabusAPI } from "@/lib/api";
import { AlertTriangle, Network, BookOpen, ArrowRight, ArrowLeft } from "lucide-react";

// Feature flag check
const FEATURE_ENABLED = process.env.NEXT_PUBLIC_FEATURE_STUDENT_CONCEPT_EXPLORER === "true";

export default function StudentConceptsPage() {
  // If feature is disabled, don't render the page
  if (!FEATURE_ENABLED) {
    return null; // Route should be hidden, but if accessed, show nothing
  }

  const [selectedYearId, setSelectedYearId] = useState<number | null>(null);
  const [selectedBlockId, setSelectedBlockId] = useState<number | null>(null);
  const [selectedThemeId, setSelectedThemeId] = useState<number | null>(null);
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(null);

  // Fetch years (use student syllabus API)
  const yearsQuery = useQuery({
    queryKey: ["syllabusYears"],
    queryFn: syllabusAPI.getYears,
    staleTime: 60000, // Cache for 60s
  });

  // Fetch blocks for selected year
  const blocksQuery = useQuery({
    queryKey: ["syllabusBlocks", selectedYearId],
    queryFn: async () => {
      if (!selectedYearId) return [];
      const year = yearsQuery.data?.find((y: any) => y.id === selectedYearId);
      if (!year) return [];
      return syllabusAPI.getBlocks(year.name);
    },
    enabled: !!selectedYearId && !!yearsQuery.data,
    staleTime: 60000,
  });

  // Fetch themes for selected block
  const themesQuery = useQuery({
    queryKey: ["syllabusThemes", selectedBlockId],
    queryFn: () => {
      if (!selectedBlockId) return Promise.resolve([]);
      return syllabusAPI.getThemes(selectedBlockId);
    },
    enabled: !!selectedBlockId,
    staleTime: 60000,
  });

  // When theme is selected, set concept_id
  const handleThemeSelect = (themeId: number) => {
    setSelectedThemeId(themeId);
    setSelectedConceptId(`theme_${themeId}`); // v1: theme_id as concept_id
  };

  // Fetch neighbors
  const neighborsQuery = useQuery({
    queryKey: ["studentGraphNeighbors", selectedConceptId],
    queryFn: () => {
      if (!selectedConceptId) return Promise.resolve(null);
      return studentGraphAPI.getStudentNeighbors(selectedConceptId, 1);
    },
    enabled: !!selectedConceptId,
    staleTime: 60000,
  });

  // Fetch prerequisites
  const prereqsQuery = useQuery({
    queryKey: ["studentGraphPrereqs", selectedConceptId],
    queryFn: () => {
      if (!selectedConceptId) return Promise.resolve(null);
      return studentGraphAPI.getStudentPrereqs(selectedConceptId, 4);
    },
    enabled: !!selectedConceptId,
    staleTime: 60000,
  });

  // Fetch suggestions
  const suggestionsQuery = useQuery({
    queryKey: ["studentGraphSuggestions", selectedConceptId],
    queryFn: () => {
      if (!selectedConceptId) return Promise.resolve(null);
      return studentGraphAPI.getStudentSuggestions(selectedConceptId, 10);
    },
    enabled: !!selectedConceptId,
    staleTime: 60000,
  });

  const neighbors = neighborsQuery.data;
  const prereqs = prereqsQuery.data;
  const suggestions = suggestionsQuery.data;

  // Check for graph unavailable errors (503)
  const hasGraphError =
    neighborsQuery.error ||
    prereqsQuery.error ||
    suggestionsQuery.error;
  const graphUnavailable =
    hasGraphError &&
    ((neighborsQuery.error as any)?.status === 503 ||
      (prereqsQuery.error as any)?.status === 503 ||
      (suggestionsQuery.error as any)?.status === 503 ||
      (neighborsQuery.error as any)?.error?.detail?.error === "graph_unavailable" ||
      (prereqsQuery.error as any)?.error?.detail?.error === "graph_unavailable" ||
      (suggestionsQuery.error as any)?.error?.detail?.error === "graph_unavailable");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Concept Explorer</h1>
        <p className="text-muted-foreground">Explore concept relationships and prerequisites</p>
      </div>

      {/* Graph Unavailable Banner */}
      {graphUnavailable && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Concept map is not available right now. Please try again later.
          </AlertDescription>
        </Alert>
      )}

      {/* Concept Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Select Concept
          </CardTitle>
          <CardDescription>Choose a concept to explore its relationships</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Year</Label>
            <Select
              value={selectedYearId?.toString() || ""}
              onValueChange={(v) => {
                setSelectedYearId(Number(v));
                setSelectedBlockId(null);
                setSelectedThemeId(null);
                setSelectedConceptId(null);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a year" />
              </SelectTrigger>
              <SelectContent>
                {yearsQuery.data?.map((year) => (
                  <SelectItem key={year.id} value={year.id.toString()}>
                    {year.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedYearId && (
            <div>
              <Label>Block</Label>
              <Select
                value={selectedBlockId?.toString() || ""}
                onValueChange={(v) => {
                  setSelectedBlockId(Number(v));
                  setSelectedThemeId(null);
                  setSelectedConceptId(null);
                }}
                disabled={blocksQuery.isLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a block" />
                </SelectTrigger>
                <SelectContent>
                  {blocksQuery.data?.map((block) => (
                    <SelectItem key={block.id} value={block.id.toString()}>
                      {block.name} ({block.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {selectedBlockId && (
            <div>
              <Label>Theme</Label>
              <Select
                value={selectedThemeId?.toString() || ""}
                onValueChange={(v) => handleThemeSelect(Number(v))}
                disabled={themesQuery.isLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a theme" />
                </SelectTrigger>
                <SelectContent>
                  {themesQuery.data?.map((theme) => (
                    <SelectItem key={theme.id} value={theme.id.toString()}>
                      {theme.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exploration Panels */}
      {selectedConceptId && !graphUnavailable && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Prerequisites Panel */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowLeft className="h-5 w-5" />
                What to learn before this
              </CardTitle>
              <CardDescription>Prerequisites for this concept</CardDescription>
            </CardHeader>
            <CardContent>
              {prereqsQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : prereqs?.nodes && prereqs.nodes.length > 0 ? (
                <div className="space-y-2">
                  {prereqs.nodes.map((node) => (
                    <ConceptListItem key={node.concept_id} node={node} />
                  ))}
                  {prereqs.truncated && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Results truncated (showing first 100)
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No prerequisites found</p>
              )}
            </CardContent>
          </Card>

          {/* Dependents Panel */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowRight className="h-5 w-5" />
                What comes next
              </CardTitle>
              <CardDescription>Concepts that depend on this</CardDescription>
            </CardHeader>
            <CardContent>
              {neighborsQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : neighbors?.dependents && neighbors.dependents.length > 0 ? (
                <div className="space-y-2">
                  {neighbors.dependents.map((node) => (
                    <ConceptListItem key={node.concept_id} node={node} />
                  ))}
                  {neighbors.truncated && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Results truncated (showing first 100)
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No dependents found</p>
              )}
            </CardContent>
          </Card>

          {/* Suggestions Panel */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                Suggested prerequisites to revise now
              </CardTitle>
              <CardDescription>Concepts you should review before this one</CardDescription>
            </CardHeader>
            <CardContent>
              {suggestionsQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : suggestions?.missing_prereqs && suggestions.missing_prereqs.length > 0 ? (
                <div className="space-y-2">
                  {suggestions.missing_prereqs.map((prereq) => (
                    <div
                      key={prereq.concept_id}
                      className="flex items-center justify-between border rounded p-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{prereq.name}</span>
                        <span className="text-xs text-muted-foreground">
                          (distance: {prereq.distance}, score: {prereq.score})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No suggestions available</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function ConceptListItem({ node }: { node: ConceptNode }) {
  return (
    <div className="flex items-center gap-2 border rounded px-3 py-2">
      <span className="font-medium">{node.name}</span>
      <Badge variant="outline">{node.level}</Badge>
      <span className="text-xs text-muted-foreground">({node.concept_id})</span>
    </div>
  );
}
