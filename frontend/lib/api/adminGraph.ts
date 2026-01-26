/** Admin Graph API client for Neo4j concept graph operations. */

import { fetcher } from "../fetcher";

export interface GraphRuntimeStatus {
  requested_mode: "disabled" | "shadow" | "active";
  effective_mode: "disabled" | "shadow" | "active";
  neo4j_enabled_env: boolean;
  reachable: boolean;
  readiness: ReadinessStatus | null;
  last_sync: LastSyncInfo | null;
}

export interface ReadinessStatus {
  ready: boolean;
  blocking_reasons: string[];
  checks: Record<string, ReadinessCheckDetails>;
}

export interface ReadinessCheckDetails {
  ok: boolean;
  details: Record<string, any>;
}

export interface LastSyncInfo {
  run_id: string;
  run_type: "incremental" | "full";
  finished_at: string | null;
  nodes_upserted: number;
  edges_upserted: number;
  cycle_detected: boolean;
}

export interface GraphSwitchRequest {
  mode: "disabled" | "shadow" | "active";
  reason: string;
  confirmation_phrase: string;
}

export interface SyncRunResponse {
  run_id: string;
  status: string;
  message: string;
}

export interface NeighborsResponse {
  concept_id: string;
  depth: number;
  prereqs: ConceptNode[];
  dependents: ConceptNode[];
  warnings: string[];
}

export interface PrerequisitesResponse {
  concept_id: string;
  max_depth: number;
  nodes: ConceptNode[];
  edges: EdgeInfo[] | null;
  warnings: string[];
}

export interface PathResponse {
  from: string;
  to: string;
  paths: PathInfo[];
  warnings: string[];
}

export interface SuggestionsResponse {
  target: string;
  missing_prereqs: MissingPrereq[];
  warnings: string[];
}

export interface ConceptNode {
  concept_id: string;
  name: string;
  level: string;
}

export interface EdgeInfo {
  from: string;
  to: string;
  weight: number;
  source: string;
}

export interface PathInfo {
  nodes: ConceptNode[];
  edges: EdgeInfo[];
}

export interface MissingPrereq {
  concept_id: string;
  name: string;
  distance: number;
  score: number;
}

/**
 * Get graph runtime status.
 */
export async function getGraphRuntime(): Promise<GraphRuntimeStatus> {
  return fetcher<GraphRuntimeStatus>("/api/admin/graph/runtime");
}

/**
 * Switch graph runtime mode.
 */
export async function switchGraphRuntime(
  request: GraphSwitchRequest
): Promise<GraphRuntimeStatus> {
  return fetcher<GraphRuntimeStatus>("/api/admin/graph/runtime/switch", {
    method: "POST",
    body: request,
  });
}

/**
 * Run incremental graph sync.
 */
export async function runGraphSyncIncremental(
  reason?: string,
  confirmation_phrase?: string
): Promise<SyncRunResponse> {
  return fetcher<SyncRunResponse>("/api/admin/graph/sync/incremental", {
    method: "POST",
    body: {
      reason,
      confirmation_phrase,
    },
  });
}

/**
 * Run full graph rebuild.
 */
export async function runGraphSyncFull(
  reason: string,
  confirmation_phrase: string
): Promise<SyncRunResponse> {
  return fetcher<SyncRunResponse>("/api/admin/graph/sync/full", {
    method: "POST",
    body: {
      reason,
      confirmation_phrase,
    },
  });
}

/**
 * Get neighbors (prerequisites and dependents) of a concept.
 */
export async function getGraphNeighbors(
  concept_id: string,
  depth: number = 1
): Promise<NeighborsResponse> {
  return fetcher<NeighborsResponse>(
    `/api/admin/graph/neighbors?concept_id=${encodeURIComponent(concept_id)}&depth=${depth}`
  );
}

/**
 * Get all prerequisites of a concept.
 */
export async function getGraphPrereqs(
  concept_id: string,
  max_depth: number = 5,
  include_edges: boolean = true
): Promise<PrerequisitesResponse> {
  return fetcher<PrerequisitesResponse>(
    `/api/admin/graph/prerequisites?concept_id=${encodeURIComponent(
      concept_id
    )}&max_depth=${max_depth}&include_edges=${include_edges}`
  );
}

/**
 * Find paths between two concepts.
 */
export async function getGraphPath(
  from_id: string,
  to_id: string,
  max_paths: number = 3,
  max_depth: number = 8
): Promise<PathResponse> {
  return fetcher<PathResponse>(
    `/api/admin/graph/path?from=${encodeURIComponent(
      from_id
    )}&to=${encodeURIComponent(to_id)}&max_paths=${max_paths}&max_depth=${max_depth}`
  );
}

/**
 * Get suggestions for missing prerequisites.
 */
export async function getGraphSuggestions(
  target_concept_id: string,
  known_concept_ids: string[],
  max_depth: number = 6,
  limit: number = 20
): Promise<SuggestionsResponse> {
  const knownIdsParam = known_concept_ids.join(",");
  return fetcher<SuggestionsResponse>(
    `/api/admin/graph/suggestions?target_concept_id=${encodeURIComponent(
      target_concept_id
    )}&known_concept_ids=${encodeURIComponent(
      knownIdsParam
    )}&max_depth=${max_depth}&limit=${limit}`
  );
}

// Export as default object for consistency with other API modules
export const adminGraphAPI = {
  getGraphRuntime,
  switchGraphRuntime,
  runGraphSyncIncremental,
  runGraphSyncFull,
  getGraphNeighbors,
  getGraphPrereqs,
  getGraphPath,
  getGraphSuggestions,
};
