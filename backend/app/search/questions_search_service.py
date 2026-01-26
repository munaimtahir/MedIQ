"""Search service for questions with ES + Postgres fallback."""

import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from elasticsearch.exceptions import ConnectionError, RequestError, TransportError
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.question_cms import Question, QuestionMedia, QuestionStatus, QuestionVersion
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole
from app.search.es_client import get_es_client, ping
from app.search.index_bootstrap import get_questions_read_alias
from app.search.questions_query import build_questions_search_query
from app.search.readiness import evaluate_elasticsearch_readiness

logger = logging.getLogger(__name__)

# Cache for ES ping result (30 seconds TTL)
_es_ping_cache: dict[str, Any] = {"result": None, "timestamp": 0}
ES_PING_CACHE_TTL = 30  # seconds


def _is_elasticsearch_available() -> tuple[bool, str | None]:
    """
    Check if Elasticsearch is available (with caching).

    Returns:
        Tuple of (is_available, fallback_reason)
    """
    if not settings.ELASTICSEARCH_ENABLED:
        return False, "elasticsearch_disabled"

    # Check cache
    now = time.time()
    if _es_ping_cache["timestamp"] > now - ES_PING_CACHE_TTL:
        is_available = _es_ping_cache["result"]
        return is_available, None if is_available else "elasticsearch_unreachable_fallback_postgres"

    # Ping ES
    try:
        is_available = ping()
        _es_ping_cache["result"] = is_available
        _es_ping_cache["timestamp"] = now
        return is_available, None if is_available else "elasticsearch_unreachable_fallback_postgres"
    except Exception as e:
        logger.warning(f"ES ping check failed: {e}")
        _es_ping_cache["result"] = False
        _es_ping_cache["timestamp"] = now
        return False, "elasticsearch_unreachable_fallback_postgres"


def _get_allowed_statuses(user: User, include_unpublished: bool) -> list[str]:
    """
    Get allowed question statuses based on user role and include_unpublished flag.

    Args:
        user: User making the request
        include_unpublished: Whether to include unpublished questions

    Returns:
        List of allowed status values
    """
    if not include_unpublished:
        return [QuestionStatus.PUBLISHED.value]

    role = UserRole(user.role)
    if role == UserRole.ADMIN:
        # ADMIN can see all statuses
        return [
            QuestionStatus.DRAFT.value,
            QuestionStatus.IN_REVIEW.value,
            QuestionStatus.APPROVED.value,
            QuestionStatus.PUBLISHED.value,
        ]
    elif role == UserRole.REVIEWER:
        # REVIEWER can see IN_REVIEW, APPROVED, PUBLISHED (not DRAFT)
        return [
            QuestionStatus.IN_REVIEW.value,
            QuestionStatus.APPROVED.value,
            QuestionStatus.PUBLISHED.value,
        ]
    else:
        # Default: only PUBLISHED
        return [QuestionStatus.PUBLISHED.value]


def _search_elasticsearch(
    q: str | None,
    filters: dict[str, Any],
    sort: str,
    page: int,
    page_size: int,
    allowed_statuses: list[str],
) -> dict[str, Any]:
    """
    Execute Elasticsearch search query.

    Returns:
        Dictionary with results, total, and facets
    """
    client = get_es_client()
    if client is None:
        raise ValueError("Elasticsearch client unavailable")

    read_alias = get_questions_read_alias()

    # Build query DSL
    include_approved = QuestionStatus.APPROVED.value in allowed_statuses
    
    # Add status to filters if multiple statuses allowed
    if len(allowed_statuses) > 1:
        filters["status"] = allowed_statuses
    
    query_dsl = build_questions_search_query(
        q=q,
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size,
        include_approved=include_approved,
    )

    # Add highlights
    query_dsl["highlight"] = {
        "fields": {
            "stem": {"fragment_size": 160, "number_of_fragments": 1},
            "explanation_plain": {"fragment_size": 160, "number_of_fragments": 1},
        }
    }

    # Add aggregations for facets
    query_dsl["aggs"] = {
        "year": {"terms": {"field": "year", "size": 100}},
        "block_id": {"terms": {"field": "block_id", "size": 100}},
        "theme_id": {"terms": {"field": "theme_id", "size": 100}},
        "cognitive_level": {"terms": {"field": "cognitive_level", "size": 100}},
        "difficulty_label": {"terms": {"field": "difficulty_label", "size": 100}},
        "source_book": {"terms": {"field": "source_book", "size": 100}},
        "status": {"terms": {"field": "status", "size": 100}},
    }

    # Execute search
    try:
        response = client.search(index=read_alias, body=query_dsl)
    except (ConnectionError, TransportError, RequestError) as e:
        logger.error(f"Elasticsearch search failed: {e}")
        raise

    # Extract results
    hits = response["hits"]
    total = hits["total"]["value"] if isinstance(hits["total"], dict) else hits["total"]

    results = []
    for hit in hits["hits"]:
        source = hit["_source"]
        highlights = hit.get("highlight", {})

        # Extract previews with highlight preference
        stem_preview = ""
        if "stem" in highlights and highlights["stem"]:
            # Remove highlight tags for preview
            stem_preview = highlights["stem"][0].replace("<em>", "").replace("</em>", "")
        else:
            stem = source.get("stem", "") or ""
            stem_preview = stem[:160] + "..." if len(stem) > 160 else stem

        explanation_preview = ""
        if "explanation_plain" in highlights and highlights["explanation_plain"]:
            # Remove highlight tags for preview
            explanation_preview = highlights["explanation_plain"][0].replace("<em>", "").replace("</em>", "")
        else:
            explanation = source.get("explanation_plain", "") or ""
            explanation_preview = explanation[:160] + "..." if len(explanation) > 160 else explanation

        tags_preview = (source.get("tags_text", "") or "")[:100]

        results.append({
            "question_id": source.get("question_id"),
            "version_id": source.get("version_id"),
            "status": source.get("status"),
            "published_at": source.get("published_at"),
            "updated_at": source.get("updated_at"),
            "year": source.get("year"),
            "block_id": source.get("block_id"),
            "theme_id": source.get("theme_id"),
            "topic_id": source.get("topic_id"),
            "cognitive_level": source.get("cognitive_level"),
            "difficulty_label": source.get("difficulty_label"),
            "source_book": source.get("source_book"),
            "source_page": source.get("source_page"),
            "stem_preview": stem_preview,
            "explanation_preview": explanation_preview,
            "tags_preview": tags_preview,
            "has_media": source.get("has_media", False),  # Use indexed value if available
        })

    # Extract facets
    aggs = response.get("aggregations", {})
    facets = {
        "year": [{"value": bucket["key"], "count": bucket["doc_count"]} for bucket in aggs.get("year", {}).get("buckets", [])],
        "block_id": [{"value": bucket["key"], "count": bucket["doc_count"]} for bucket in aggs.get("block_id", {}).get("buckets", [])],
        "theme_id": [{"value": bucket["key"], "count": bucket["doc_count"]} for bucket in aggs.get("theme_id", {}).get("buckets", [])],
        "cognitive_level": [{"value": bucket["key"], "count": bucket["doc_count"]} for bucket in aggs.get("cognitive_level", {}).get("buckets", [])],
        "difficulty_label": [{"value": bucket["key"], "count": bucket["doc_count"]} for bucket in aggs.get("difficulty_label", {}).get("buckets", [])],
        "source_book": [{"value": bucket["key"], "count": bucket["doc_count"]} for bucket in aggs.get("source_book", {}).get("buckets", [])],
        "status": [{"value": bucket["key"], "count": bucket["doc_count"]} for bucket in aggs.get("status", {}).get("buckets", [])],
    }

    return {
        "results": results,
        "total": total,
        "facets": facets,
    }


def _search_postgres(
    db: Session,
    q: str | None,
    filters: dict[str, Any],
    sort: str,
    page: int,
    page_size: int,
    allowed_statuses: list[str],
) -> dict[str, Any]:
    """
    Execute Postgres fallback search query.

    Returns:
        Dictionary with results, total, and facets
    """
    # Base query
    query = db.query(Question).filter(Question.status.in_(allowed_statuses))

    # Apply filters
    if "year" in filters and filters["year"] is not None:
        # Join to get year
        query = query.join(Block).join(Year).filter(Year.order_no == filters["year"])

    if "block_id" in filters and filters["block_id"] is not None:
        query = query.filter(Question.block_id == int(filters["block_id"]))

    if "theme_id" in filters and filters["theme_id"] is not None:
        query = query.filter(Question.theme_id == int(filters["theme_id"]))

    if "topic_id" in filters and filters["topic_id"] is not None:
        query = query.filter(Question.topic_id == int(filters["topic_id"]))

    # Note: concept_id filter is not supported in Postgres fallback (not indexed)
    # It will be silently ignored

    if "cognitive_level" in filters and filters["cognitive_level"]:
        query = query.filter(Question.cognitive_level.in_(filters["cognitive_level"]))

    if "difficulty_label" in filters and filters["difficulty_label"]:
        query = query.filter(Question.difficulty.in_(filters["difficulty_label"]))

    if "source_book" in filters and filters["source_book"]:
        query = query.filter(Question.source_book.in_(filters["source_book"]))

    if "status" in filters and filters["status"]:
        # Intersect with allowed statuses
        allowed_filter_statuses = [s for s in filters["status"] if s in allowed_statuses]
        if allowed_filter_statuses:
            query = query.filter(Question.status.in_(allowed_filter_statuses))

    # Text search (simple ILIKE fallback)
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Question.stem.ilike(search_term),
                Question.explanation_md.ilike(search_term),
                # TODO: Add tags search if tags are stored separately
            )
        )

    # Get total count
    total = query.count()

    # Apply sorting
    if sort == "published_at_desc":
        query = query.order_by(Question.published_at.desc().nulls_last())
    elif sort == "updated_at_desc":
        query = query.order_by(Question.updated_at.desc().nulls_last())
    else:
        # Default: published_at desc
        query = query.order_by(Question.published_at.desc().nulls_last())

    # Pagination
    offset = (page - 1) * page_size
    questions = query.offset(offset).limit(page_size).all()

    # Build results
    results = []
    for question in questions:
        # Get latest version
        version = (
            db.query(QuestionVersion)
            .filter(QuestionVersion.question_id == question.id)
            .order_by(QuestionVersion.version_no.desc())
            .first()
        )

        # Get syllabus names
        block_name = None
        theme_name = None
        year = None
        if question.block_id:
            block = db.query(Block).filter(Block.id == question.block_id).first()
            if block:
                block_name = block.name
                if block.year_id:
                    year_obj = db.query(Year).filter(Year.id == block.year_id).first()
                    if year_obj:
                        year = year_obj.order_no

        if question.theme_id:
            theme = db.query(Theme).filter(Theme.id == question.theme_id).first()
            if theme:
                theme_name = theme.title

        # Extract source_page as integer
        source_page_int = None
        if question.source_page:
            import re
            match = re.search(r"(\d+)", question.source_page)
            if match:
                try:
                    source_page_int = int(match.group(1))
                except ValueError:
                    pass

        # Build previews
        stem_preview = (question.stem or "")[:160] + "..." if question.stem and len(question.stem) > 160 else (question.stem or "")
        explanation_preview = (question.explanation_md or "")[:160] + "..." if question.explanation_md and len(question.explanation_md) > 160 else (question.explanation_md or "")
        tags_preview = ""  # TODO: Add tags if available

        # Check for media attachments
        has_media = (
            db.query(QuestionMedia)
            .filter(QuestionMedia.question_id == question.id)
            .first()
            is not None
        )

        results.append({
            "question_id": str(question.id),
            "version_id": str(version.id) if version else None,
            "status": question.status.value,
            "published_at": question.published_at.isoformat() if question.published_at else None,
            "updated_at": question.updated_at.isoformat() if question.updated_at else None,
            "year": year,
            "block_id": str(question.block_id) if question.block_id else None,
            "theme_id": str(question.theme_id) if question.theme_id else None,
            "topic_id": str(question.topic_id) if question.topic_id else None,
            "cognitive_level": question.cognitive_level,
            "difficulty_label": question.difficulty,
            "source_book": question.source_book,
            "source_page": source_page_int,
            "stem_preview": stem_preview,
            "explanation_preview": explanation_preview,
            "tags_preview": tags_preview,
            "has_media": has_media,
        })

    # Compute facets (Option 1: partial facets only)
    # Compute simple facets for status, cognitive_level, difficulty_label, source_book
    facets = {
        "year": [],  # Empty with warning
        "block_id": [],  # Empty with warning
        "theme_id": [],  # Empty with warning
        "cognitive_level": [],
        "difficulty_label": [],
        "source_book": [],
        "status": [],
    }

    # Status facet
    status_counts = (
        db.query(Question.status, func.count(Question.id))
        .filter(Question.status.in_(allowed_statuses))
        .group_by(Question.status)
        .all()
    )
    facets["status"] = [{"value": status.value, "count": count} for status, count in status_counts]

    # Cognitive level facet
    cognitive_counts = (
        db.query(Question.cognitive_level, func.count(Question.id))
        .filter(Question.status.in_(allowed_statuses))
        .filter(Question.cognitive_level.isnot(None))
        .group_by(Question.cognitive_level)
        .all()
    )
    facets["cognitive_level"] = [{"value": level, "count": count} for level, count in cognitive_counts if level]

    # Difficulty facet
    difficulty_counts = (
        db.query(Question.difficulty, func.count(Question.id))
        .filter(Question.status.in_(allowed_statuses))
        .filter(Question.difficulty.isnot(None))
        .group_by(Question.difficulty)
        .all()
    )
    facets["difficulty_label"] = [{"value": diff, "count": count} for diff, count in difficulty_counts if diff]

    # Source book facet
    source_counts = (
        db.query(Question.source_book, func.count(Question.id))
        .filter(Question.status.in_(allowed_statuses))
        .filter(Question.source_book.isnot(None))
        .group_by(Question.source_book)
        .all()
    )
    facets["source_book"] = [{"value": book, "count": count} for book, count in source_counts if book]

    return {
        "results": results,
        "total": total,
        "facets": facets,
    }


def search_questions_admin(
    db: Session,
    user: User,
    q: str | None = None,
    year: int | None = None,
    block_id: str | None = None,
    theme_id: str | None = None,
    topic_id: str | None = None,
    concept_id: list[str] | None = None,
    cognitive_level: list[str] | None = None,
    difficulty_label: list[str] | None = None,
    source_book: list[str] | None = None,
    status: list[str] | None = None,
    include_unpublished: bool = False,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """
    Search questions with ES + Postgres fallback.

    Returns:
        Search response with stable contract
    """
    start_time = time.time()

    # Get allowed statuses
    allowed_statuses = _get_allowed_statuses(user, include_unpublished)

    # Build filters dict
    filters: dict[str, Any] = {}
    if year is not None:
        filters["year"] = year
    if block_id is not None:
        filters["block_id"] = block_id
    if theme_id is not None:
        filters["theme_id"] = theme_id
    if topic_id is not None:
        filters["topic_id"] = topic_id
    if concept_id:
        filters["concept_id"] = list(set(concept_id))  # Dedupe
    if cognitive_level:
        filters["cognitive_level"] = list(set(cognitive_level))  # Dedupe
    if difficulty_label:
        filters["difficulty_label"] = list(set(difficulty_label))  # Dedupe
    if source_book:
        filters["source_book"] = list(set(source_book))  # Dedupe
    if status:
        # Filter to only allowed statuses
        filters["status"] = [s for s in list(set(status)) if s in allowed_statuses]

    # Get runtime mode (defaults to "postgres" if not set)
    from app.models.algo_runtime import AlgoRuntimeConfig
    runtime_config = db.query(AlgoRuntimeConfig).first()
    requested_mode = "postgres"
    if runtime_config and runtime_config.config_json:
        requested_mode = runtime_config.config_json.get("search_engine_mode", "postgres")

    # Determine effective engine based on runtime mode and readiness
    engine = "postgres"
    warnings = []
    requested_es = False

    if requested_mode == "postgres":
        # Runtime mode is postgres - always use postgres
        engine = "postgres"
    elif requested_mode == "elasticsearch":
        # Runtime mode requests elasticsearch - check readiness gate
        requested_es = True
        
        # Evaluate readiness (shadow gate)
        readiness = evaluate_elasticsearch_readiness(db)
        
        if readiness.ready:
            # All readiness checks passed - use Elasticsearch
            engine = "elasticsearch"
        else:
            # Readiness gate blocked - fallback to Postgres
            engine = "postgres"
            warnings.append("elasticsearch_not_ready")
            # Add blocking reasons as additional warnings
            for reason in readiness.blocking_reasons:
                warnings.append(f"readiness_blocked: {reason}")
    else:
        # Invalid mode - default to postgres
        logger.warning(f"Invalid search_engine_mode: {requested_mode}, defaulting to postgres")
        engine = "postgres"

    # Execute search
    try:
        if engine == "elasticsearch":
            search_result = _search_elasticsearch(
                q=q,
                filters=filters,
                sort=sort,
                page=page,
                page_size=page_size,
                allowed_statuses=allowed_statuses,
            )
        else:
            search_result = _search_postgres(
                db=db,
                q=q,
                filters=filters,
                sort=sort,
                page=page,
                page_size=page_size,
                allowed_statuses=allowed_statuses,
            )
            # Add warning for degraded facets
            if not search_result["facets"]["year"] and not search_result["facets"]["block_id"]:
                warnings.append("facets_degraded_postgres")
    except Exception as e:
        logger.error(f"Search failed, falling back to Postgres: {e}", exc_info=True)
        # Fallback to Postgres on any error (even if runtime requested ES)
        engine = "postgres"
        if requested_es:
            warnings.append("elasticsearch_unreachable_fallback_postgres")
        search_result = _search_postgres(
            db=db,
            q=q,
            filters=filters,
            sort=sort,
            page=page,
            page_size=page_size,
            allowed_statuses=allowed_statuses,
        )
        if not search_result["facets"]["year"] and not search_result["facets"]["block_id"]:
            warnings.append("facets_degraded_postgres")

    query_time_ms = int((time.time() - start_time) * 1000)

    # Log observability and audit
    logger.info(
        f"Search request: requested_mode={requested_mode}, effective_engine={engine}, "
        f"query_time_ms={query_time_ms}, total={search_result['total']}, "
        f"warnings={warnings}",
        extra={
            "search_engine_requested": requested_mode,
            "search_engine_effective": engine,
            "readiness_blocked": "elasticsearch_not_ready" in warnings,
        },
    )
    
    # Audit log if readiness blocked
    if requested_es and "elasticsearch_not_ready" in warnings:
        logger.warning(
            "Search engine switch requested but readiness blocked",
            extra={
                "search_engine_switch_requested": "elasticsearch",
                "readiness_blocked": True,
                "blocking_reasons": [w for w in warnings if w.startswith("readiness_blocked:")],
            },
        )

    # Build response
    response = {
        "engine": engine,
        "total": search_result["total"],
        "page": page,
        "page_size": page_size,
        "results": search_result["results"],
        "facets": search_result["facets"],
        "warnings": warnings,
    }

    return response
