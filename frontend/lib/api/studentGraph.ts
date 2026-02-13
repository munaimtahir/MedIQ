/** Student Graph API client for concept exploration (feature-flagged). */

import { fetcher } from "../fetcher";

export interface ConceptNode {
  concept_id: string;
  name: string;
  level: string;
}

export interface NeighborsResponse {
  concept_id: string;
  depth: number;
  prereqs: ConceptNode[];
  dependents: ConceptNode[];
  warnings: string[];
  truncated: boolean;
}

export interface PrerequisitesResponse {
  concept_id: string;
  max_depth: number;
  nodes: ConceptNode[];
  warnings: string[];
  truncated: boolean;
}

export interface SuggestionsResponse {
  target: string;
  missing_prereqs: Array<{
    concept_id: string;
    name: string;
    distance: number;
    score: number;
  }>;
  warnings: string[];
  truncated: boolean;
}

/**
 * Get neighbors (prerequisites and dependents) of a concept.
 */
export async function getStudentNeighbors(
  concept_id: string,
  depth: number = 1
): Promise<NeighborsResponse> {
  return fetcher<NeighborsResponse>(
    `/api/student/graph/neighbors?concept_id=${encodeURIComponent(concept_id)}&depth=${depth}`
  );
}

/**
 * Get all prerequisites of a concept.
 */
export async function getStudentPrereqs(
  concept_id: string,
  max_depth: number = 4
): Promise<PrerequisitesResponse> {
  return fetcher<PrerequisitesResponse>(
    `/api/student/graph/prerequisites?concept_id=${encodeURIComponent(
      concept_id
    )}&max_depth=${max_depth}`
  );
}

/**
 * Get suggestions for missing prerequisites.
 */
export async function getStudentSuggestions(
  target_concept_id: string,
  limit: number = 10
): Promise<SuggestionsResponse> {
  return fetcher<SuggestionsResponse>(
    `/api/student/graph/suggestions?target_concept_id=${encodeURIComponent(
      target_concept_id
    )}&limit=${limit}`
  );
}

export const studentGraphAPI = {
  getStudentNeighbors,
  getStudentPrereqs,
  getStudentSuggestions,
};
