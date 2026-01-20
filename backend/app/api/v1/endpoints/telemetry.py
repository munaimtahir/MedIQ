"""Telemetry ingestion endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.question_cms import Question
from app.models.session import SessionQuestion, TestSession
from app.models.user import User
from app.schemas.telemetry import TelemetryBatchResponse, TelemetryBatchSubmit
from app.services.telemetry import log_events_bulk

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


async def validate_event_ownership(
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID,
    question_id: UUID | None = None,
) -> tuple[bool, str | None]:
    """
    Validate that user owns the session and question belongs to session.

    Returns:
        Tuple of (is_valid, error_reason)
    """
    # Check session ownership
    session_stmt = select(TestSession).where(TestSession.id == session_id)
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if not session:
        return False, f"Session {session_id} not found"

    if session.user_id != user_id:
        return False, f"Session {session_id} not owned by user"

    # If question_id provided, verify it belongs to session
    if question_id:
        question_stmt = select(SessionQuestion).where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.question_id == question_id,
        )
        question_result = await db.execute(question_stmt)
        session_question = question_result.scalar_one_or_none()

        if not session_question:
            return False, f"Question {question_id} not in session {session_id}"

    return True, None


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/telemetry/events", response_model=TelemetryBatchResponse)
async def ingest_telemetry_batch(
    batch: TelemetryBatchSubmit,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Ingest a batch of telemetry events from client.

    Validates ownership and membership before storing events.
    Returns count of accepted/rejected events with sample rejection reasons.

    NOTE: This is best-effort. Invalid events are skipped without failing the batch.
    """
    accepted = 0
    rejected = 0
    rejection_reasons = []

    # Validate and collect events
    valid_events = []

    for event in batch.events:
        try:
            # Validate ownership and membership
            is_valid, error_reason = await validate_event_ownership(
                db,
                current_user.id,
                event.session_id,
                event.question_id,
            )

            if not is_valid:
                rejected += 1
                if len(rejection_reasons) < 5:
                    rejection_reasons.append(error_reason)
                continue

            # Event is valid, add to batch
            valid_events.append(
                {
                    "session_id": event.session_id,
                    "event_type": event.event_type.value,
                    "client_ts": event.client_ts,
                    "seq": event.seq,
                    "question_id": event.question_id,
                    "payload": event.payload,
                }
            )

        except Exception as e:
            rejected += 1
            if len(rejection_reasons) < 5:
                rejection_reasons.append(f"Validation error: {str(e)}")
            logger.warning(f"Event validation failed: {e}")

    # Bulk insert valid events
    try:
        accepted_count, rejected_count = await log_events_bulk(
            db,
            current_user.id,
            valid_events,
            source=batch.source,
        )
        accepted += accepted_count
        rejected += rejected_count

        await db.commit()

    except Exception as e:
        logger.error(f"Failed to insert telemetry batch: {e}", exc_info=True)
        # Best-effort: don't fail the request
        rejected += len(valid_events)
        if len(rejection_reasons) < 5:
            rejection_reasons.append(f"Insert error: {str(e)}")

    return TelemetryBatchResponse(
        accepted=accepted,
        rejected=rejected,
        rejected_reasons_sample=rejection_reasons,
    )
