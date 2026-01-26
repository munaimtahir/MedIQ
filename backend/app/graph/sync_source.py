"""Source data adapter: Maps Postgres tables to Concept graph format.

This module provides adapters to map existing Postgres schema (themes, topics, prereq_edges)
to the Concept graph schema defined in Task 133.

Since the system currently uses themes/topics rather than a dedicated concepts table,
this adapter creates Concept nodes from themes and topics.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.graph_revision import PrereqEdge
from app.models.syllabus import Block, Theme, Year

logger = logging.getLogger(__name__)


def get_concepts_since_watermark(
    db: Session,
    watermark: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Get concepts (mapped from themes/topics) updated since watermark.

    Maps themes to Concept nodes with:
    - concept_id: f"theme_{theme.id}"
    - level: "THEME"
    - name: theme.title
    - year, block_id, theme_id from relationships

    Args:
        db: Database session
        watermark: Only return concepts updated after this timestamp

    Returns:
        List of concept dictionaries ready for Neo4j upsert
    """
    query = select(Theme).join(Block).join(Year).where(Theme.is_active == True)

    if watermark:
        # Only get themes updated after watermark
        query = query.where(Theme.updated_at >= watermark)
    # If no watermark, get all active themes (for first sync or full rebuild)

    themes = db.execute(query).scalars().all()

    concepts = []
    for theme in themes:
        # Get year order_no from block
        year_order_no = None
        if theme.block and theme.block.year:
            year_order_no = theme.block.year.order_no

        concept = {
            "concept_id": f"theme_{theme.id}",
            "name": theme.title,
            "year": year_order_no,
            "block_id": str(theme.block_id) if theme.block_id else None,
            "theme_id": str(theme.id),
            "topic_id": None,
            "level": "THEME",
            "is_active": theme.is_active,
            "updated_at": (theme.updated_at or theme.created_at or datetime.now(UTC)).isoformat(),
        }
        concepts.append(concept)

    return concepts


def get_all_active_concepts(db: Session) -> list[dict[str, Any]]:
    """
    Get all active concepts (for full rebuild).

    Returns:
        List of all active concept dictionaries
    """
    return get_concepts_since_watermark(db, watermark=None)


def get_prereq_edges_since_watermark(
    db: Session,
    watermark: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Get prerequisite edges updated since watermark, mapped to concept IDs.

    Maps PrereqEdge (theme-to-theme) to concept-to-concept edges:
    - from_concept_id: f"theme_{edge.from_theme_id}"
    - to_concept_id: f"theme_{edge.to_theme_id}"

    Args:
        db: Database session
        watermark: Only return edges updated after this timestamp

    Returns:
        List of edge dictionaries with from_id, to_id, and properties
    """
    query = select(PrereqEdge).where(PrereqEdge.is_active == True)

    if watermark:
        # Only get edges updated after watermark
        query = query.where(PrereqEdge.updated_at >= watermark)
    # If no watermark, get all active edges (for first sync or full rebuild)

    edges = db.execute(query).scalars().all()

    mapped_edges = []
    for edge in edges:
        # Map theme IDs to concept IDs
        from_concept_id = f"theme_{edge.from_theme_id}"
        to_concept_id = f"theme_{edge.to_theme_id}"

        # Skip self-loops (shouldn't happen but safety check)
        if from_concept_id == to_concept_id:
            logger.warning(f"Skipping self-loop edge: {from_concept_id} -> {to_concept_id}")
            continue

        edge_dict = {
            "from_id": from_concept_id,
            "to_id": to_concept_id,
            "props": {
                "weight": float(edge.weight),
                "source": edge.source.upper() if edge.source else "MANUAL",  # manual -> MANUAL
                "is_active": edge.is_active,
                "created_at": edge.created_at.isoformat() if edge.created_at else None,
                "updated_at": edge.updated_at.isoformat() if edge.updated_at else datetime.utcnow().isoformat(),
                "notes": None,  # PrereqEdge doesn't have notes field currently
            },
        }
        mapped_edges.append(edge_dict)

    return mapped_edges


def get_all_active_prereq_edges(db: Session) -> list[dict[str, Any]]:
    """
    Get all active prerequisite edges (for full rebuild).

    Returns:
        List of all active edge dictionaries
    """
    return get_prereq_edges_since_watermark(db, watermark=None)


def get_inactive_concepts_since_watermark(
    db: Session,
    watermark: datetime | None = None,
) -> list[str]:
    """
    Get concept IDs that became inactive since watermark.

    Args:
        db: Database session
        watermark: Only check concepts updated after this timestamp

    Returns:
        List of concept_id strings that should be inactivated in Neo4j
    """
    query = select(Theme).where(Theme.is_active == False)

    if watermark:
        query = query.where(Theme.updated_at >= watermark)

    themes = db.execute(query).scalars().all()

    return [f"theme_{theme.id}" for theme in themes]


def get_inactive_edges_since_watermark(
    db: Session,
    watermark: datetime | None = None,
) -> list[tuple[str, str]]:
    """
    Get edge pairs (from_id, to_id) that became inactive since watermark.

    Args:
        db: Database session
        watermark: Only check edges updated after this timestamp

    Returns:
        List of (from_concept_id, to_concept_id) tuples
    """
    query = select(PrereqEdge).where(PrereqEdge.is_active == False)

    if watermark:
        query = query.where(PrereqEdge.updated_at >= watermark)

    edges = db.execute(query).scalars().all()

    return [
        (f"theme_{edge.from_theme_id}", f"theme_{edge.to_theme_id}")
        for edge in edges
        if edge.from_theme_id != edge.to_theme_id  # Skip self-loops
    ]
