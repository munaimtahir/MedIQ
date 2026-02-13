"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { ErrorState } from "@/components/status/ErrorState";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminGraphAPI, type GraphRuntimeStatus } from "@/lib/api/adminGraph";
import { notify } from "@/lib/notify";
import {
  Database,
  Network,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Copy,
  Search,
} from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";

export default function GraphViewerPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(
    searchParams.get("concept_id")
  );
  const [switchModalOpen, setSwitchModalOpen] = useState(false);
  const [switchMode, setSwitchMode] = useState<"disabled" | "shadow" | "active">("disabled");
  const [switchReason, setSwitchReason] = useState("");
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [syncType, setSyncType] = useState<"incremental" | "full">("incremental");
  const [syncReason, setSyncReason] = useState("");

  // Runtime status query (refetch every 30s on focus)
  const runtimeQuery = useQuery({
    queryKey: ["graphRuntime"],
    queryFn: adminGraphAPI.getGraphRuntime,
    refetchInterval: 30000,
    refetchOnWindowFocus: true,
  });

  // Switch mutation
  const switchMutation = useMutation({
    mutationFn: adminGraphAPI.switchGraphRuntime,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["graphRuntime"] });
      notify.success("Graph mode switched successfully");
      setSwitchModalOpen(false);
      setSwitchReason("");
    },
    onError: (error: Error) => {
      notify.error(error.message || "Failed to switch graph mode");
    },
  });

  // Sync mutations
  const incrementalSyncMutation = useMutation({
    mutationFn: (reason?: string) =>
      adminGraphAPI.runGraphSyncIncremental(reason, "RUN GRAPH SYNC"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["graphRuntime"] });
      notify.success("Incremental sync started");
      setSyncModalOpen(false);
      setSyncReason("");
    },
    onError: (error: Error) => {
      notify.error(error.message || "Failed to start sync");
    },
  });

  const fullSyncMutation = useMutation({
    mutationFn: (reason: string) =>
      adminGraphAPI.runGraphSyncFull(reason, "RUN GRAPH FULL REBUILD"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["graphRuntime"] });
      notify.success("Full rebuild started");
      setSyncModalOpen(false);
      setSyncReason("");
    },
    onError: (error: Error) => {
      notify.error(error.message || "Failed to start rebuild");
    },
  });

  const status = runtimeQuery.data;
  const loading = runtimeQuery.isLoading;
  const error = runtimeQuery.error;

  // Update URL when concept changes
  useEffect(() => {
    if (selectedConceptId) {
      router.replace(`/admin/graph?concept_id=${encodeURIComponent(selectedConceptId)}`);
    } else {
      router.replace("/admin/graph");
    }
  }, [selectedConceptId, router]);

  const handleSwitchMode = (mode: "disabled" | "shadow" | "active") => {
    setSwitchMode(mode);
    setSwitchReason("");
    setSwitchModalOpen(true);
  };

  const handleConfirmSwitch = async () => {
    const phrases = {
      disabled: "SWITCH GRAPH TO DISABLED",
      shadow: "SWITCH GRAPH TO SHADOW",
      active: "SWITCH GRAPH TO ACTIVE",
    };
    await switchMutation.mutateAsync({
      mode: switchMode,
      reason: switchReason,
      confirmation_phrase: phrases[switchMode],
    });
  };

  const handleSync = (type: "incremental" | "full") => {
    setSyncType(type);
    setSyncReason("");
    setSyncModalOpen(true);
  };

  const handleConfirmSync = async () => {
    if (syncType === "incremental") {
      await incrementalSyncMutation.mutateAsync(syncReason);
    } else {
      await fullSyncMutation.mutateAsync(syncReason);
    }
  };

  const getModePillVariant = (mode: string) => {
    switch (mode) {
      case "active":
        return "default";
      case "shadow":
        return "secondary";
      case "disabled":
        return "outline";
      default:
        return "outline";
    }
  };

  if (loading && !status) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Graph Viewer</h1>
            <p className="text-muted-foreground">Neo4j concept graph operations and exploration</p>
          </div>
        </div>
        <SkeletonTable rows={5} cols={3} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Graph Viewer</h1>
            <p className="text-muted-foreground">Neo4j concept graph operations and exploration</p>
          </div>
        </div>
        <ErrorState
          variant="card"
          title="Failed to load graph status"
          description={(error as Error).message || "An error occurred while loading graph status."}
          actionLabel="Retry"
          onAction={() => runtimeQuery.refetch()}
        />
      </div>
    );
  }

  const effectiveMode = status?.effective_mode || "disabled";
  const isDisabled = effectiveMode === "disabled";
  const readiness = status?.readiness;
  const isReady = readiness?.ready ?? false;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Graph Viewer</h1>
          <p className="text-muted-foreground">Neo4j concept graph operations and exploration</p>
        </div>
        <Button variant="outline" onClick={() => runtimeQuery.refetch()} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Graph Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5" />
            Graph Status
          </CardTitle>
          <CardDescription>Neo4j concept graph runtime configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <Label className="text-xs text-muted-foreground">Requested Mode</Label>
                <Badge variant={getModePillVariant(status?.requested_mode || "disabled")} className="ml-2">
                  {status?.requested_mode || "disabled"}
                </Badge>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Effective Mode</Label>
                <Badge variant={getModePillVariant(effectiveMode)} className="ml-2">
                  {effectiveMode}
                </Badge>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Readiness</Label>
                <Badge
                  variant={isReady ? "default" : "destructive"}
                  className="ml-2"
                >
                  {isReady ? "READY" : "NOT READY"}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                {status?.reachable ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
                <span className="text-sm">{status?.reachable ? "UP" : "DOWN"}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSwitchMode("disabled")}
              >
                Disable
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSwitchMode("shadow")}
                disabled={!isReady}
              >
                Enable Shadow
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSwitchMode("active")}
                disabled={!isReady}
              >
                Enable Active
              </Button>
            </div>
          </div>

          {readiness && !isReady && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-2">Blocking Reasons:</div>
                <ul className="list-disc list-inside space-y-1">
                  {readiness.blocking_reasons.map((reason, idx) => (
                    <li key={idx} className="text-sm">
                      {reason}
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {status?.last_sync && (
            <div className="text-sm text-muted-foreground">
              Last sync: {status.last_sync.run_type} -{" "}
              {status.last_sync.finished_at
                ? formatDistanceToNow(new Date(status.last_sync.finished_at), { addSuffix: true })
                : "unknown"}
              {" - "}
              {status.last_sync.nodes_upserted} nodes, {status.last_sync.edges_upserted} edges
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSync("incremental")}
              disabled={isDisabled}
            >
              Run Incremental Sync
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSync("full")}
              disabled={isDisabled}
            >
              Run Full Rebuild
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Degraded Banner */}
      {isDisabled && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Graph is not available. {readiness && (
              <>
                Blocking reasons: {readiness.blocking_reasons.join(", ")}.{" "}
                <Button
                  variant="link"
                  className="p-0 h-auto"
                  onClick={() => handleSync("incremental")}
                >
                  Run Sync
                </Button>
                {" or "}
                <Button
                  variant="link"
                  className="p-0 h-auto"
                  onClick={() => handleSwitchMode("shadow")}
                >
                  Enable Shadow
                </Button>
              </>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Concept Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Concept Selector</CardTitle>
          <CardDescription>Select a concept to explore</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label htmlFor="concept-id">Concept ID</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  id="concept-id"
                  placeholder="e.g., theme_123"
                  value={selectedConceptId || ""}
                  onChange={(e) => setSelectedConceptId(e.target.value || null)}
                />
                <Button
                  variant="outline"
                  onClick={() => {
                    // For v1, allow manual entry
                    // TODO: Add Year -> Block -> Theme selector when concept table exists
                  }}
                >
                  <Search className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                For v1, enter theme ID as concept_id (e.g., theme_123)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Explorer Panel */}
      {selectedConceptId && !isDisabled && (
        <Card>
          <CardHeader>
            <CardTitle>Graph Explorer</CardTitle>
            <CardDescription>Explore concept relationships</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="neighbors">
              <TabsList>
                <TabsTrigger value="neighbors">Neighbors</TabsTrigger>
                <TabsTrigger value="prereqs">Prerequisites</TabsTrigger>
                <TabsTrigger value="path">Path</TabsTrigger>
                <TabsTrigger value="suggestions">Suggestions</TabsTrigger>
              </TabsList>
              <TabsContent value="neighbors">
                <NeighborsTab conceptId={selectedConceptId} />
              </TabsContent>
              <TabsContent value="prereqs">
                <PrerequisitesTab conceptId={selectedConceptId} />
              </TabsContent>
              <TabsContent value="path">
                <PathTab conceptId={selectedConceptId} />
              </TabsContent>
              <TabsContent value="suggestions">
                <SuggestionsTab conceptId={selectedConceptId} />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Switch Modal */}
      <PoliceConfirmModal
        open={switchModalOpen}
        onOpenChange={setSwitchModalOpen}
        actionTitle={`Switch Graph to ${switchMode.toUpperCase()}`}
        requiredPhrase={
          switchMode === "disabled"
            ? "SWITCH GRAPH TO DISABLED"
            : switchMode === "shadow"
            ? "SWITCH GRAPH TO SHADOW"
            : "SWITCH GRAPH TO ACTIVE"
        }
        reason={switchReason}
        onReasonChange={setSwitchReason}
        onConfirm={handleConfirmSwitch}
        isSubmitting={switchMutation.isPending}
      />

      {/* Sync Modal */}
      <PoliceConfirmModal
        open={syncModalOpen}
        onOpenChange={setSyncModalOpen}
        actionTitle={`Run ${syncType === "incremental" ? "Incremental Sync" : "Full Rebuild"}`}
        requiredPhrase={
          syncType === "incremental" ? "RUN GRAPH SYNC" : "RUN GRAPH FULL REBUILD"
        }
        reason={syncReason}
        onReasonChange={setSyncReason}
        onConfirm={handleConfirmSync}
        isSubmitting={incrementalSyncMutation.isPending || fullSyncMutation.isPending}
      />
    </div>
  );
}

// Explorer Tab Components
function NeighborsTab({ conceptId }: { conceptId: string }) {
  const [depth, setDepth] = useState(1);
  const { data, isLoading, error } = useQuery({
    queryKey: ["graphNeighbors", conceptId, depth],
    queryFn: () => adminGraphAPI.getGraphNeighbors(conceptId, depth),
    enabled: !!conceptId,
  });

  if (isLoading) return <div>Loading neighbors...</div>;
  if (error) return <div>Error: {(error as Error).message}</div>;
  if (!data) return null;

  return (
    <div className="space-y-4 mt-4">
      <div className="flex items-center gap-2">
        <Label>Depth:</Label>
        <Select value={depth.toString()} onValueChange={(v) => setDepth(parseInt(v))}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">1</SelectItem>
            <SelectItem value="2">2</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <h3 className="font-semibold mb-2">Prerequisites ({data.prereqs.length})</h3>
          <div className="space-y-2">
            {data.prereqs.map((node) => (
              <ConceptChip key={node.concept_id} node={node} />
            ))}
          </div>
        </div>
        <div>
          <h3 className="font-semibold mb-2">Dependents ({data.dependents.length})</h3>
          <div className="space-y-2">
            {data.dependents.map((node) => (
              <ConceptChip key={node.concept_id} node={node} />
            ))}
          </div>
        </div>
      </div>
      {data.warnings.length > 0 && (
        <Alert variant="warning">
          <AlertDescription>
            {data.warnings.map((w, i) => (
              <div key={i}>{w}</div>
            ))}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function PrerequisitesTab({ conceptId }: { conceptId: string }) {
  const [maxDepth, setMaxDepth] = useState(5);
  const [includeEdges, setIncludeEdges] = useState(true);
  const { data, isLoading, error } = useQuery({
    queryKey: ["graphPrereqs", conceptId, maxDepth, includeEdges],
    queryFn: () => adminGraphAPI.getGraphPrereqs(conceptId, maxDepth, includeEdges),
    enabled: !!conceptId,
  });

  if (isLoading) return <div>Loading prerequisites...</div>;
  if (error) return <div>Error: {(error as Error).message}</div>;
  if (!data) return null;

  return (
    <div className="space-y-4 mt-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Label>Max Depth:</Label>
          <Select value={maxDepth.toString()} onValueChange={(v) => setMaxDepth(parseInt(v))}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[1, 2, 3, 4, 5].map((d) => (
                <SelectItem key={d} value={d.toString()}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="include-edges"
            checked={includeEdges}
            onChange={(e) => setIncludeEdges(e.target.checked)}
          />
          <Label htmlFor="include-edges">Include Edges</Label>
        </div>
      </div>
      <div>
        <h3 className="font-semibold mb-2">Prerequisites ({data.nodes.length})</h3>
        <div className="space-y-2">
          {data.nodes.map((node) => (
            <ConceptChip key={node.concept_id} node={node} />
          ))}
        </div>
      </div>
      {data.warnings.length > 0 && (
        <Alert variant="warning">
          <AlertDescription>
            {data.warnings.map((w, i) => (
              <div key={i}>{w}</div>
            ))}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function PathTab({ conceptId }: { conceptId: string }) {
  const [toId, setToId] = useState("");
  const [maxDepth, setMaxDepth] = useState(8);
  const { data, isLoading, error } = useQuery({
    queryKey: ["graphPath", conceptId, toId, maxDepth],
    queryFn: () => adminGraphAPI.getGraphPath(conceptId, toId, 3, maxDepth),
    enabled: !!conceptId && !!toId,
  });

  return (
    <div className="space-y-4 mt-4">
      <div className="flex items-center gap-2">
        <Label>To Concept ID:</Label>
        <Input
          value={toId}
          onChange={(e) => setToId(e.target.value)}
          placeholder="e.g., theme_456"
          className="w-48"
        />
        <Label>Max Depth:</Label>
        <Select value={maxDepth.toString()} onValueChange={(v) => setMaxDepth(parseInt(v))}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[3, 5, 8, 10].map((d) => (
              <SelectItem key={d} value={d.toString()}>
                {d}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {isLoading && <div>Finding path...</div>}
      {error && <div>Error: {(error as Error).message}</div>}
      {data && (
        <div className="space-y-4">
          {data.paths.map((path, idx) => (
            <div key={idx} className="border rounded p-4">
              <h4 className="font-semibold mb-2">Path {idx + 1}</h4>
              <div className="flex flex-wrap gap-2">
                {path.nodes.map((node) => (
                  <ConceptChip key={node.concept_id} node={node} />
                ))}
              </div>
            </div>
          ))}
          {data.warnings.length > 0 && (
            <Alert variant="warning">
              <AlertDescription>
                {data.warnings.map((w, i) => (
                  <div key={i}>{w}</div>
                ))}
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}
    </div>
  );
}

function SuggestionsTab({ conceptId }: { conceptId: string }) {
  const [knownIds, setKnownIds] = useState<string[]>([]);
  const [knownIdInput, setKnownIdInput] = useState("");
  const [maxDepth, setMaxDepth] = useState(6);
  const [limit, setLimit] = useState(20);
  const { data, isLoading, error } = useQuery({
    queryKey: ["graphSuggestions", conceptId, knownIds, maxDepth, limit],
    queryFn: () => adminGraphAPI.getGraphSuggestions(conceptId, knownIds, maxDepth, limit),
    enabled: !!conceptId,
  });

  const addKnownId = () => {
    if (knownIdInput.trim() && knownIds.length < 50) {
      setKnownIds([...knownIds, knownIdInput.trim()]);
      setKnownIdInput("");
    }
  };

  return (
    <div className="space-y-4 mt-4">
      <div className="flex items-center gap-2">
        <Label>Known Concept IDs ({knownIds.length}/50):</Label>
        <Input
          value={knownIdInput}
          onChange={(e) => setKnownIdInput(e.target.value)}
          placeholder="e.g., theme_123"
          className="w-48"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addKnownId();
            }
          }}
        />
        <Button variant="outline" size="sm" onClick={addKnownId} disabled={knownIds.length >= 50}>
          Add
        </Button>
      </div>
      {knownIds.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {knownIds.map((id, idx) => (
            <Badge key={idx} variant="secondary">
              {id}
              <button
                className="ml-2"
                onClick={() => setKnownIds(knownIds.filter((_, i) => i !== idx))}
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
      )}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Label>Max Depth:</Label>
          <Select value={maxDepth.toString()} onValueChange={(v) => setMaxDepth(parseInt(v))}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[3, 4, 5, 6, 8].map((d) => (
                <SelectItem key={d} value={d.toString()}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Label>Limit:</Label>
          <Select value={limit.toString()} onValueChange={(v) => setLimit(parseInt(v))}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[10, 20, 30, 50].map((l) => (
                <SelectItem key={l} value={l.toString()}>
                  {l}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      {isLoading && <div>Getting suggestions...</div>}
      {error && <div>Error: {(error as Error).message}</div>}
      {data && (
        <div className="space-y-2">
          <h3 className="font-semibold">Missing Prerequisites ({data.missing_prereqs.length})</h3>
          {data.missing_prereqs.map((prereq) => (
            <div key={prereq.concept_id} className="flex items-center justify-between border rounded p-2">
              <div>
                <ConceptChip node={prereq} />
                <span className="text-xs text-muted-foreground ml-2">
                  distance: {prereq.distance}, score: {prereq.score}
                </span>
              </div>
            </div>
          ))}
          {data.warnings.length > 0 && (
            <Alert variant="warning">
              <AlertDescription>
                {data.warnings.map((w, i) => (
                  <div key={i}>{w}</div>
                ))}
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}
    </div>
  );
}

function ConceptChip({
  node,
}: {
  node: { concept_id: string; name: string; level?: string; distance?: number; score?: number };
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(node.concept_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-2 border rounded px-3 py-1.5">
      <span className="font-medium">{node.name}</span>
      {node.level && <Badge variant="outline">{node.level}</Badge>}
      <span className="text-xs text-muted-foreground">({node.concept_id})</span>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0"
        onClick={handleCopy}
        title="Copy concept_id"
      >
        <Copy className={`h-3 w-3 ${copied ? "text-green-500" : ""}`} />
      </Button>
    </div>
  );
}
