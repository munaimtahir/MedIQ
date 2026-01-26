"""Nightly reindex job for full rebuild of questions index."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from elasticsearch.exceptions import ConnectionError, RequestError, TransportError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.question_cms import Question, QuestionStatus
from app.models.search_indexing import SearchSyncRun, SearchSyncRunStatus, SearchSyncRunType
from app.search.document_builder import build_question_document
from app.search.es_client import get_es_client
from app.search.index_bootstrap import (
    create_questions_index,
    get_current_questions_index,
    get_questions_write_alias,
    swap_questions_aliases,
)

logger = logging.getLogger(__name__)


def check_freeze_updates(db: Session) -> bool:
    """Check if freeze_updates is enabled (sync version)."""
    try:
        config = db.query(AlgoRuntimeConfig).limit(1).first()
        if not config:
            return False
        config_json = config.config_json or {}
        safe_mode = config_json.get("safe_mode", {})
        return safe_mode.get("freeze_updates", False)
    except Exception as e:
        logger.warning(f"Failed to check freeze_updates: {e}")
        return False


def run_nightly_reindex(db: Session) -> SearchSyncRun:
    """
    Run nightly reindex job (full rebuild).

    Args:
        db: Database session

    Returns:
        SearchSyncRun record
    """
    # Create run record
    run = SearchSyncRun(
        id=uuid4(),
        run_type=SearchSyncRunType.NIGHTLY,
        status=SearchSyncRunStatus.QUEUED,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # Check if ES is enabled
        if not settings.ELASTICSEARCH_ENABLED:
            run.status = SearchSyncRunStatus.DISABLED
            run.details = {"reason": "Elasticsearch disabled"}
            run.finished_at = datetime.now(UTC)
            db.commit()
            logger.info("Nightly reindex skipped: Elasticsearch disabled")
            return run

        # Check freeze_updates
        if check_freeze_updates(db):
            run.status = SearchSyncRunStatus.BLOCKED_FROZEN
            run.details = {"reason": "freeze_updates is enabled"}
            run.finished_at = datetime.now(UTC)
            db.commit()
            logger.info("Nightly reindex blocked: freeze_updates is enabled")
            return run

        # Start run
        run.status = SearchSyncRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        db.commit()

        # Get ES client
        client = get_es_client()
        if client is None:
            raise ValueError("Elasticsearch client unavailable")

        # Create new index with timestamp
        new_index_name = create_questions_index()
        logger.info(f"Created new index: {new_index_name}")

        # Get write alias for bulk operations
        write_alias = get_questions_write_alias()

        # Count expected published questions
        expected_count = db.query(Question).filter(Question.status == QuestionStatus.PUBLISHED).count()
        logger.info(f"Expected {expected_count} published questions to index")

        # Stream published questions and bulk index
        indexed_count = 0
        deleted_count = 0
        failed_count = 0
        batch_size = settings.ELASTICSEARCH_BULK_BATCH_SIZE
        batch = []

        # Use server-side cursor for large datasets
        query = db.query(Question).filter(Question.status == QuestionStatus.PUBLISHED)
        
        # Process in batches
        offset = 0
        while True:
            questions = query.offset(offset).limit(batch_size).all()
            if not questions:
                break

            for question in questions:
                try:
                    doc = build_question_document(db, question)
                    if doc:
                        doc_id = f"{doc['question_id']}:{doc['version_id']}"
                        batch.append({
                            "_index": new_index_name,
                            "_id": doc_id,
                            "_source": doc,
                        })
                        indexed_count += 1
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to build document for question {question.id}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error building document for question {question.id}: {e}")

            # Bulk index batch
            if batch:
                try:
                    from elasticsearch.helpers import bulk
                    success, failed_items = bulk(client, batch, raise_on_error=False)
                    if failed_items:
                        failed_count += len(failed_items)
                        logger.warning(f"Bulk index had {len(failed_items)} failures")
                    batch = []
                except (ConnectionError, TransportError, RequestError) as e:
                    logger.error(f"Bulk index failed: {e}")
                    failed_count += len(batch)
                    batch = []

            offset += batch_size

        # Index any remaining items
        if batch:
            try:
                from elasticsearch.helpers import bulk
                success, failed_items = bulk(client, batch, raise_on_error=False)
                if failed_items:
                    failed_count += len(failed_items)
            except (ConnectionError, TransportError, RequestError) as e:
                logger.error(f"Final bulk index failed: {e}")
                failed_count += len(batch)

        logger.info(f"Indexed {indexed_count} documents, {failed_count} failed")

        # Verify doc count
        actual_count = None
        try:
            stats = client.indices.stats(index=new_index_name)
            actual_count = stats["indices"][new_index_name]["total"]["docs"]["count"]
            logger.info(f"Index has {actual_count} documents (expected ~{expected_count})")

            # Tolerance: allow 5% difference
            tolerance = max(1, int(expected_count * 0.05))
            if abs(actual_count - expected_count) > tolerance:
                raise ValueError(
                    f"Document count mismatch: expected ~{expected_count}, got {actual_count}"
                )
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            # Don't swap aliases if verification fails
            run.status = SearchSyncRunStatus.FAILED
            run.finished_at = datetime.now(UTC)
            run.indexed_count = indexed_count
            run.failed_count = failed_count
            run.details = {
                "error": str(e),
                "new_index": new_index_name,
                "actual_count": actual_count,
                "expected_count": expected_count,
            }
            db.commit()
            return run

        # Sample query to verify index works
        try:
            sample_result = client.search(
                index=new_index_name,
                body={"query": {"match_all": {}}, "size": 1},
            )
            if sample_result["hits"]["total"]["value"] == 0 and expected_count > 0:
                raise ValueError("Sample query returned no results but expected documents exist")
        except Exception as e:
            logger.error(f"Sample query failed: {e}")
            run.status = SearchSyncRunStatus.FAILED
            run.finished_at = datetime.now(UTC)
            run.indexed_count = indexed_count
            run.failed_count = failed_count
            run.details = {
                "error": f"Sample query failed: {str(e)}",
                "new_index": new_index_name,
            }
            db.commit()
            return run

        # Atomic alias swap
        try:
            swap_questions_aliases(new_index_name)
            logger.info(f"Swapped aliases to {new_index_name}")
        except Exception as e:
            logger.error(f"Alias swap failed: {e}")
            run.status = SearchSyncRunStatus.FAILED
            run.finished_at = datetime.now(UTC)
            run.indexed_count = indexed_count
            run.failed_count = failed_count
            run.details = {
                "error": f"Alias swap failed: {str(e)}",
                "new_index": new_index_name,
            }
            db.commit()
            return run

        # Optionally delete old indices (keep last 2)
        try:
            current_index = get_current_questions_index()
            if current_index:
                # Get all questions indices
                indices = client.indices.get(index=f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_v1_*")
                index_names = sorted(indices.keys(), reverse=True)
                
                # Keep current index and one previous, delete the rest
                indices_to_delete = index_names[2:]  # Skip first 2 (current + one backup)
                for old_index in indices_to_delete:
                    try:
                        client.indices.delete(index=old_index)
                        logger.info(f"Deleted old index: {old_index}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old index {old_index}: {e}")
        except Exception as e:
            logger.warning(f"Failed to clean up old indices: {e}")
            # Don't fail the run for cleanup errors

        # Mark as done
        run.status = SearchSyncRunStatus.DONE
        run.finished_at = datetime.now(UTC)
        run.indexed_count = indexed_count
        run.deleted_count = deleted_count
        run.failed_count = failed_count
        run.details = {
            "new_index": new_index_name,
            "expected_count": expected_count,
            "actual_count": actual_count,
        }
        db.commit()

        logger.info(f"Nightly reindex completed: {indexed_count} indexed, {failed_count} failed")
        return run

    except Exception as e:
        logger.error(f"Nightly reindex failed: {e}", exc_info=True)
        run.status = SearchSyncRunStatus.FAILED
        run.finished_at = datetime.now(UTC)
        run.details = {"error": str(e)}
        db.commit()
        return run
