"""Offline sync endpoints for mobile clients."""

import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.redis_client import get_redis_client
from app.middleware.idempotency import IDEMPOTENCY_KEY_PREFIX, compute_payload_hash
from app.models.session import SessionAnswer, SessionStatus, TestSession
from app.models.user import User
from app.schemas.sync import (
    BatchSyncRequest,
    BatchSyncResponse,
    SyncAttemptItem,
    SyncAttemptResult,
)

router = APIRouter(prefix="/sync", tags=["Offline Sync"])


def compute_attempt_payload_hash(attempt: SyncAttemptItem) -> str:
    """Compute hash of attempt payload for idempotency."""
    payload = {
        "question_id": str(attempt.question_id),
        "selected_option_index": attempt.selected_option_index,
        "answered_at": attempt.answered_at.isoformat(),
    }
    payload_json = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_json.encode()).hexdigest()


def get_or_create_offline_session(
    db: Session,
    user_id: UUID,
    offline_session_id: UUID,
    attempt: SyncAttemptItem,
) -> TestSession:
    """
    Get or create server session for offline session.
    
    Maps offline_session_id to a real TestSession deterministically.
    Uses Redis to store mapping for consistency.
    """
    redis_client = get_redis_client()
    
    # Check Redis for existing mapping
    if redis_client:
        mapping_key = f"offline_session:{offline_session_id}"
        stored_session_id = redis_client.get(mapping_key)
        
        if stored_session_id:
            session = db.query(TestSession).filter(
                TestSession.id == UUID(stored_session_id),
                TestSession.user_id == user_id,
            ).first()
            
            if session:
                return session
    
    # Create new session for offline_session_id
    from app.models.session import SessionMode
    from app.models.question_cms import Question
    
    # Get question to determine scope
    question = db.query(Question).filter(Question.id == attempt.question_id).first()
    year = question.year_id if question and question.year_id else 1
    blocks_json = []
    themes_json = []
    
    if question:
        if question.block_id:
            blocks_json = [question.block_id]
        if question.theme_id:
            themes_json = [question.theme_id]
    
    session = TestSession(
        user_id=user_id,
        mode=SessionMode.TUTOR,  # Default mode for offline sessions
        status=SessionStatus.ACTIVE,
        year=year,
        blocks_json=blocks_json,
        themes_json=themes_json,
        total_questions=1,  # Will be updated as more attempts sync
    )
    db.add(session)
    db.flush()  # Get session.id
    
    # Store mapping in Redis
    if redis_client:
        mapping_key = f"offline_session:{offline_session_id}"
        redis_client.setex(mapping_key, 86400 * 7, str(session.id))  # 7 days TTL
    
    return session


async def process_single_attempt(
    db: Session,
    user_id: UUID,
    attempt: SyncAttemptItem,
) -> SyncAttemptResult:
    """
    Process a single attempt from batch sync.
    
    Returns result with status: acked, duplicate, or rejected.
    """
    redis_client = get_redis_client()
    
    # Compute payload hash
    computed_hash = compute_attempt_payload_hash(attempt)
    
    # Verify client-provided hash matches
    if attempt.payload_hash != computed_hash:
        return SyncAttemptResult(
            client_attempt_id=attempt.client_attempt_id,
            status="rejected",
            error_code="PAYLOAD_HASH_MISMATCH",
            message="Payload hash does not match computed hash",
        )
    
    # Check idempotency (Redis)
    if redis_client:
        redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{attempt.idempotency_key}"
        stored_data = redis_client.get(redis_key)
        
        if stored_data:
            # Already processed - return duplicate
            stored = json.loads(stored_data)
            return SyncAttemptResult(
                client_attempt_id=attempt.client_attempt_id,
                status="duplicate",
                server_attempt_id=UUID(stored.get("server_attempt_id")) if stored.get("server_attempt_id") else None,
                server_session_id=UUID(stored.get("server_session_id")) if stored.get("server_session_id") else None,
            )
    
    # Get or create session
    if attempt.session_id:
        # Use existing session
        session = db.query(TestSession).filter(
            TestSession.id == attempt.session_id,
            TestSession.user_id == user_id,
        ).first()
        
        if not session:
            return SyncAttemptResult(
                client_attempt_id=attempt.client_attempt_id,
                status="rejected",
                error_code="SESSION_NOT_FOUND",
                message="Session not found or access denied",
            )
    elif attempt.offline_session_id:
        # Map offline session to server session
        session = get_or_create_offline_session(db, user_id, attempt.offline_session_id, attempt)
    else:
        return SyncAttemptResult(
            client_attempt_id=attempt.client_attempt_id,
            status="rejected",
            error_code="SESSION_REQUIRED",
            message="Either session_id or offline_session_id must be provided",
        )
    
    # Check if answer already exists (idempotency at DB level)
    existing_answer = db.query(SessionAnswer).filter(
        SessionAnswer.session_id == session.id,
        SessionAnswer.question_id == attempt.question_id,
    ).first()
    
    if existing_answer:
        # Already exists - treat as duplicate (idempotent)
        if redis_client:
            # Store in Redis for future checks
            redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{attempt.idempotency_key}"
            stored_data = {
                "payload_hash": computed_hash,
                "server_attempt_id": str(existing_answer.id),
                "server_session_id": str(session.id),
            }
            redis_client.setex(redis_key, 86400, json.dumps(stored_data))  # 24h TTL
        
        return SyncAttemptResult(
            client_attempt_id=attempt.client_attempt_id,
            status="duplicate",
            server_attempt_id=existing_answer.id,
            server_session_id=session.id,
        )
    
    # Create new answer
    from app.models.question_cms import Question
    
    question = db.query(Question).filter(Question.id == attempt.question_id).first()
    if not question:
        return SyncAttemptResult(
            client_attempt_id=attempt.client_attempt_id,
            status="rejected",
            error_code="QUESTION_NOT_FOUND",
            message="Question not found",
        )
    
    # Compute correctness using frozen correct_index
    is_correct = question.correct_index == attempt.selected_option_index if question.correct_index is not None else None
    
    answer = SessionAnswer(
        session_id=session.id,
        question_id=attempt.question_id,
        selected_index=attempt.selected_option_index,
        is_correct=is_correct,
        answered_at=attempt.answered_at,
        marked_for_review=False,  # Default
    )
    db.add(answer)
    db.flush()  # Get answer.id
    
    # Store in Redis for idempotency
    if redis_client:
        redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{attempt.idempotency_key}"
        stored_data = {
            "payload_hash": computed_hash,
            "server_attempt_id": str(answer.id),
            "server_session_id": str(session.id),
        }
        redis_client.setex(redis_key, 86400, json.dumps(stored_data))  # 24h TTL
    
    return SyncAttemptResult(
        client_attempt_id=attempt.client_attempt_id,
        status="acked",
        server_attempt_id=answer.id,
        server_session_id=session.id,
    )


@router.post("/attempts:batch", response_model=BatchSyncResponse)
async def batch_sync_attempts(
    request: BatchSyncRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BatchSyncResponse:
    """
    Batch sync offline attempts to server.
    
    Processes each attempt independently with idempotency.
    Returns status per attempt: acked, duplicate, or rejected.
    
    **Idempotency**: Each attempt uses idempotency_key to prevent duplicates.
    **Atomicity**: Each attempt is processed independently (not per-batch).
    **Safety**: Server NEVER double-applies scoring.
    """
    if len(request.attempts) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one attempt required",
        )
    
    if len(request.attempts) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 attempts per batch",
        )
    
    results = []
    
    # Process each attempt independently
    for attempt in request.attempts:
        try:
            result = await process_single_attempt(db, current_user.id, attempt)
            results.append(result)
            
            # Commit per attempt (atomic per item, not per batch)
            if result.status == "acked":
                db.commit()
            else:
                # For duplicates/rejected, rollback any partial changes
                db.rollback()
        except Exception as e:
            # Error processing attempt - reject it
            db.rollback()
            results.append(
                SyncAttemptResult(
                    client_attempt_id=attempt.client_attempt_id,
                    status="rejected",
                    error_code="PROCESSING_ERROR",
                    message=str(e),
                )
            )
    
    return BatchSyncResponse(results=results)
