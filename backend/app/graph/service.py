"""Neo4j graph service layer for read-only graph queries.

This module provides bounded, safe graph queries for admin APIs.
All queries are bounded with limits and timeouts to prevent runaway expansions.
"""

import logging
from typing import Any

from app.core.config import settings
from app.graph.neo4j_client import ping, run_read

logger = logging.getLogger(__name__)

# Hard caps for safety
MAX_NEIGHBORS_DEPTH = 2
MAX_PREREQS_DEPTH = 8
MAX_PATH_DEPTH = 10
MAX_PATH_COUNT = 5
MAX_SUGGESTIONS_KNOWN_IDS = 200
MAX_SUGGESTIONS_LIMIT = 50
MAX_NODES_RESULT = 500  # Cap for prerequisites expansion


def _check_neo4j_available() -> tuple[bool, dict[str, Any] | None]:
    """
    Check if Neo4j is enabled and reachable.

    Returns:
        Tuple of (is_available, error_details)
    """
    if not settings.NEO4J_ENABLED:
        return False, {"error": "neo4j_disabled", "message": "Graph is disabled in this environment."}

    is_reachable, _, ping_details = ping()
    if not is_reachable:
        return False, {
            "error": "neo4j_unreachable",
            "message": "Neo4j is unreachable",
            "details": ping_details,
        }

    return True, None


def get_neighbors(concept_id: str, depth: int = 1) -> dict[str, Any]:
    """
    Get neighbors (prerequisites and dependents) of a concept.

    Args:
        concept_id: Concept ID to query
        depth: Depth of expansion (1 or 2)

    Returns:
        Dictionary with prereqs and dependents lists, plus warnings
    """
    available, error = _check_neo4j_available()
    if not available:
        raise ValueError(f"Neo4j unavailable: {error}")

    if depth > MAX_NEIGHBORS_DEPTH:
        depth = MAX_NEIGHBORS_DEPTH

    warnings = []

    # Get prerequisites (incoming edges)
    prereqs = []
    if depth == 1:
        cypher = """
        MATCH (p:Concept)-[r:PREREQ]->(c:Concept {concept_id: $concept_id})
        WHERE r.is_active = true AND p.is_active = true
        RETURN DISTINCT p.concept_id as concept_id, p.name as name, p.level as level
        ORDER BY p.name
        LIMIT 100
        """
    else:  # depth == 2
        cypher = """
        MATCH (p:Concept)-[r:PREREQ*1..2]->(c:Concept {concept_id: $concept_id})
        WHERE ALL(rel IN r WHERE rel.is_active = true)
          AND ALL(node IN nodes(p)[0..-1] WHERE node.is_active = true)
        RETURN DISTINCT p.concept_id as concept_id, p.name as name, p.level as level
        ORDER BY p.name
        LIMIT 200
        """

    try:
        results = run_read(cypher, {"concept_id": concept_id})
        prereqs = [
            {
                "concept_id": r.get("concept_id"),
                "name": r.get("name"),
                "level": r.get("level"),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"Error fetching prerequisites for {concept_id}: {e}")
        warnings.append(f"Failed to fetch prerequisites: {str(e)}")

    # Get dependents (outgoing edges)
    dependents = []
    if depth == 1:
        cypher = """
        MATCH (c:Concept {concept_id: $concept_id})-[r:PREREQ]->(d:Concept)
        WHERE r.is_active = true AND d.is_active = true
        RETURN DISTINCT d.concept_id as concept_id, d.name as name, d.level as level
        ORDER BY d.name
        LIMIT 100
        """
    else:  # depth == 2
        cypher = """
        MATCH (c:Concept {concept_id: $concept_id})-[r:PREREQ*1..2]->(d:Concept)
        WHERE ALL(rel IN r WHERE rel.is_active = true)
          AND d.is_active = true
        WITH DISTINCT d
        RETURN d.concept_id as concept_id, d.name as name, d.level as level
        ORDER BY d.name
        LIMIT 200
        """

    try:
        results = run_read(cypher, {"concept_id": concept_id})
        dependents = [
            {
                "concept_id": r.get("concept_id"),
                "name": r.get("name"),
                "level": r.get("level"),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"Error fetching dependents for {concept_id}: {e}")
        warnings.append(f"Failed to fetch dependents: {str(e)}")

    return {
        "concept_id": concept_id,
        "depth": depth,
        "prereqs": prereqs,
        "dependents": dependents,
        "warnings": warnings,
    }


def get_prereqs(concept_id: str, max_depth: int = 5, include_edges: bool = True) -> dict[str, Any]:
    """
    Get all prerequisites of a concept up to max_depth.

    Args:
        concept_id: Concept ID to query
        max_depth: Maximum depth to expand (capped at MAX_PREREQS_DEPTH)
        include_edges: Whether to include edge details

    Returns:
        Dictionary with nodes and edges (if requested), plus warnings
    """
    available, error = _check_neo4j_available()
    if not available:
        raise ValueError(f"Neo4j unavailable: {error}")

    if max_depth > MAX_PREREQS_DEPTH:
        max_depth = MAX_PREREQS_DEPTH

    warnings = []

    # Get all prerequisite nodes
    cypher = """
    MATCH p = (prereq:Concept)-[r:PREREQ*1..$max_depth]->(c:Concept {concept_id: $concept_id})
    WHERE ALL(rel IN r WHERE rel.is_active = true)
      AND ALL(node IN nodes(p)[0..-1] WHERE node.is_active = true)
    WITH DISTINCT prereq
    RETURN prereq.concept_id as concept_id, prereq.name as name, prereq.level as level
    ORDER BY prereq.name
    LIMIT $max_nodes
    """
    params = {
        "concept_id": concept_id,
        "max_depth": max_depth,
        "max_nodes": MAX_NODES_RESULT,
    }

    try:
        results = run_read(cypher, params)
        nodes = [
            {
                "concept_id": r.get("concept_id"),
                "name": r.get("name"),
                "level": r.get("level"),
            }
            for r in results
        ]

        if len(nodes) >= MAX_NODES_RESULT:
            warnings.append("result_truncated: Prerequisites expansion exceeded node limit")

    except Exception as e:
        logger.warning(f"Error fetching prerequisites for {concept_id}: {e}")
        raise ValueError(f"Failed to fetch prerequisites: {str(e)}")

    edges = []
    if include_edges:
        # Get edges between all prerequisite nodes and target
        node_ids = [n["concept_id"] for n in nodes]
        if node_ids:
            # Get edges in the prerequisite chain
            cypher = """
            MATCH p = (prereq:Concept)-[r:PREREQ*1..$max_depth]->(c:Concept {concept_id: $concept_id})
            WHERE ALL(rel IN r WHERE rel.is_active = true)
              AND prereq.concept_id IN $node_ids
            UNWIND relationships(p) as rel
            WITH DISTINCT rel, startNode(rel) as from_node, endNode(rel) as to_node
            WHERE rel.is_active = true
            RETURN from_node.concept_id as from, to_node.concept_id as to,
                   rel.weight as weight, rel.source as source
            ORDER BY from, to
            LIMIT 1000
            """
            try:
                edge_results = run_read(cypher, {"concept_id": concept_id, "max_depth": max_depth, "node_ids": node_ids})
                edges = [
                    {
                        "from": r.get("from"),
                        "to": r.get("to"),
                        "weight": r.get("weight"),
                        "source": r.get("source"),
                    }
                    for r in edge_results
                ]
            except Exception as e:
                logger.warning(f"Error fetching prerequisite edges for {concept_id}: {e}")
                warnings.append(f"Failed to fetch edges: {str(e)}")

    return {
        "concept_id": concept_id,
        "max_depth": max_depth,
        "nodes": nodes,
        "edges": edges if include_edges else None,
        "warnings": warnings,
    }


def get_path(from_id: str, to_id: str, max_paths: int = 3, max_depth: int = 8) -> dict[str, Any]:
    """
    Find paths between two concepts.

    Args:
        from_id: Source concept ID
        to_id: Target concept ID
        max_paths: Maximum number of paths to return (capped at MAX_PATH_COUNT)
        max_depth: Maximum path depth (capped at MAX_PATH_DEPTH)

    Returns:
        Dictionary with paths (nodes and edges) and warnings
    """
    available, error = _check_neo4j_available()
    if not available:
        raise ValueError(f"Neo4j unavailable: {error}")

    if max_paths > MAX_PATH_COUNT:
        max_paths = MAX_PATH_COUNT
    if max_depth > MAX_PATH_DEPTH:
        max_depth = MAX_PATH_DEPTH

    warnings = []
    paths = []

    # Use shortestPath query that explicitly extracts nodes and relationships
    cypher = """
    MATCH (a:Concept {concept_id: $from_id}), (b:Concept {concept_id: $to_id})
    MATCH p = shortestPath((a)-[:PREREQ*..$max_depth]->(b))
    WHERE ALL(rel IN relationships(p) WHERE rel.is_active = true)
      AND ALL(node IN nodes(p) WHERE node.is_active = true)
    WITH p, length(p) as path_length
    ORDER BY path_length
    LIMIT $max_paths
    RETURN 
        [node IN nodes(p) | {concept_id: node.concept_id, name: node.name, level: node.level}] as path_nodes,
        [rel IN relationships(p) | {
            from: startNode(rel).concept_id,
            to: endNode(rel).concept_id,
            weight: rel.weight,
            source: rel.source
        }] as path_edges,
        path_length
    ORDER BY path_length
    """

    try:
        results = run_read(cypher, {"from_id": from_id, "to_id": to_id, "max_depth": max_depth, "max_paths": max_paths})
        
        for r in results:
            path_nodes = r.get("path_nodes", [])
            path_edges = r.get("path_edges", [])
            paths.append({
                "nodes": path_nodes,
                "edges": path_edges,
            })

        if len(paths) == 0:
            warnings.append("No path found between concepts")
        elif len(paths) < max_paths:
            warnings.append("multi_path_limited_without_apoc: Only shortest path returned (APOC not available for k-shortest)")

    except Exception as e:
        logger.warning(f"Error finding path from {from_id} to {to_id}: {e}")
        warnings.append(f"Path query failed: {str(e)}")

    return {
        "from": from_id,
        "to": to_id,
        "paths": paths,
        "warnings": warnings,
    }


def get_suggestions(
    target_concept_id: str,
    known_concept_ids: list[str],
    max_depth: int = 6,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Suggest missing prerequisites for a target concept.

    Args:
        target_concept_id: Target concept ID
        known_concept_ids: List of concept IDs the user already knows
        max_depth: Maximum depth to expand (capped at MAX_PREREQS_DEPTH)
        limit: Maximum number of suggestions (capped at MAX_SUGGESTIONS_LIMIT)

    Returns:
        Dictionary with missing_prereqs (ranked by score) and warnings
    """
    available, error = _check_neo4j_available()
    if not available:
        raise ValueError(f"Neo4j unavailable: {error}")

    if max_depth > MAX_PREREQS_DEPTH:
        max_depth = MAX_PREREQS_DEPTH
    if limit > MAX_SUGGESTIONS_LIMIT:
        limit = MAX_SUGGESTIONS_LIMIT

    warnings = []

    # Get all prerequisites of target
    cypher = """
    MATCH p = (prereq:Concept)-[r:PREREQ*1..$max_depth]->(target:Concept {concept_id: $target_id})
    WHERE ALL(rel IN r WHERE rel.is_active = true)
      AND ALL(node IN nodes(p)[0..-1] WHERE node.is_active = true)
    WITH prereq, min(length(p)) as distance
    WHERE prereq.concept_id NOT IN $known_ids
    RETURN DISTINCT prereq.concept_id as concept_id, prereq.name as name, distance
    ORDER BY distance, prereq.name
    LIMIT $limit
    """
    params = {
        "target_id": target_concept_id,
        "known_ids": known_concept_ids or [],
        "max_depth": max_depth,
        "limit": limit,
    }

    try:
        results = run_read(cypher, params)
        missing_prereqs = []
        for r in results:
            distance = r.get("distance", 1)
            score = 1.0 / (distance + 1)  # Score inversely proportional to distance
            missing_prereqs.append({
                "concept_id": r.get("concept_id"),
                "name": r.get("name"),
                "distance": distance,
                "score": round(score, 2),
            })

    except Exception as e:
        logger.warning(f"Error getting suggestions for {target_concept_id}: {e}")
        raise ValueError(f"Failed to get suggestions: {str(e)}")

    return {
        "target": target_concept_id,
        "missing_prereqs": missing_prereqs,
        "warnings": warnings,
    }
