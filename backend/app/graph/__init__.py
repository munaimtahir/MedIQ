"""Neo4j graph database module for concept graph (shadow infrastructure)."""

from app.graph.neo4j_client import get_driver, ping, run_read, run_write
from app.graph.schema import ensure_constraints_and_indexes
from app.graph.health import get_graph_health
from app.graph.cypher import upsert_concept_node, upsert_prereq_edge, deactivate_missing_edges
from app.graph.concept_sync import run_incremental_sync, run_full_rebuild
from app.graph import api as graph_api

__all__ = [
    "get_driver",
    "ping",
    "run_read",
    "run_write",
    "ensure_constraints_and_indexes",
    "get_graph_health",
    "upsert_concept_node",
    "upsert_prereq_edge",
    "deactivate_missing_edges",
    "run_incremental_sync",
    "run_full_rebuild",
    "graph_api",
]
