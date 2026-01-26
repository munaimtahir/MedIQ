"""Query builder for questions search."""

from typing import Any

from app.search.es_client import get_es_client


def build_questions_search_query(
    q: str | None = None,
    filters: dict[str, Any] | None = None,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
    include_approved: bool = False,
) -> dict[str, Any]:
    """
    Build Elasticsearch query DSL for questions search.

    Args:
        q: Search query string (optional)
        filters: Dictionary of filter criteria:
            - year: int
            - block_id: str
            - theme_id: str
            - topic_id: str
            - cognitive_level: str
            - difficulty_label: str
            - source_book: str
        sort: Sort option ("relevance", "published_at_desc", "updated_at_desc")
        page: Page number (1-based)
        page_size: Results per page
        include_approved: If True, include APPROVED questions. Default False (PUBLISHED only).

    Returns:
        Elasticsearch query DSL dictionary.
    """
    filters = filters or {}

    # Build must clauses (all must match)
    must_clauses = []

    # Status filter (default to PUBLISHED only)
    # Note: If status is in filters, it will be handled in filter_clauses
    # Only add default status filter if status is not explicitly filtered
    if "status" not in filters:
        if include_approved:
            must_clauses.append({"terms": {"status": ["PUBLISHED", "APPROVED"]}})
        else:
            must_clauses.append({"term": {"status": "PUBLISHED"}})

    # Text search (if query provided)
    if q and q.strip():
        must_clauses.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": [
                        "stem^3",  # Stem has highest weight
                        "tags_text^2",  # Tags have medium weight
                        "explanation_plain^1",  # Explanation has lower weight
                    ],
                    "type": "best_fields",
                    "operator": "and",  # All terms must match
                }
            }
        )

    # Build filter clauses (filters don't affect relevance score)
    filter_clauses = []

    if "year" in filters and filters["year"] is not None:
        filter_clauses.append({"term": {"year": filters["year"]}})

    if "block_id" in filters and filters["block_id"] is not None:
        filter_clauses.append({"term": {"block_id": str(filters["block_id"])}})

    if "theme_id" in filters and filters["theme_id"] is not None:
        filter_clauses.append({"term": {"theme_id": str(filters["theme_id"])}})

    if "topic_id" in filters and filters["topic_id"] is not None:
        filter_clauses.append({"term": {"topic_id": str(filters["topic_id"])}})

    # Note: concept_id filter is supported via concept_ids array field
    if "concept_id" in filters and filters["concept_id"] is not None:
        concept_ids = filters["concept_id"]
        if isinstance(concept_ids, list):
            filter_clauses.append({"terms": {"concept_ids": concept_ids}})
        else:
            filter_clauses.append({"term": {"concept_ids": concept_ids}})

    if "cognitive_level" in filters and filters["cognitive_level"] is not None:
        level = filters["cognitive_level"]
        if isinstance(level, list):
            filter_clauses.append({"terms": {"cognitive_level": level}})
        else:
            filter_clauses.append({"term": {"cognitive_level": level}})

    if "difficulty_label" in filters and filters["difficulty_label"] is not None:
        difficulty = filters["difficulty_label"]
        if isinstance(difficulty, list):
            filter_clauses.append({"terms": {"difficulty_label": difficulty}})
        else:
            filter_clauses.append({"term": {"difficulty_label": difficulty}})

    if "source_book" in filters and filters["source_book"] is not None:
        book = filters["source_book"]
        if isinstance(book, list):
            filter_clauses.append({"terms": {"source_book": book}})
        else:
            filter_clauses.append({"term": {"source_book": book}})

    if "status" in filters and filters["status"] is not None:
        status = filters["status"]
        if isinstance(status, list):
            filter_clauses.append({"terms": {"status": status}})
        else:
            filter_clauses.append({"term": {"status": status}})

    # Build sort
    sort_clause = []
    if sort == "relevance" and q:
        # Default relevance sort (score descending)
        sort_clause.append("_score")
    elif sort == "published_at_desc":
        sort_clause.append({"published_at": {"order": "desc"}})
    elif sort == "updated_at_desc":
        sort_clause.append({"updated_at": {"order": "desc"}})
    else:
        # Default to published_at desc if no query or unknown sort
        if q:
            sort_clause.append("_score")
        sort_clause.append({"published_at": {"order": "desc"}})

    # Build final query
    query: dict[str, Any] = {
        "query": {
            "bool": {
                "must": must_clauses,
            }
        },
        "sort": sort_clause,
        "from": (page - 1) * page_size,
        "size": page_size,
    }

    # Add filters if any
    if filter_clauses:
        query["query"]["bool"]["filter"] = filter_clauses

    return query
