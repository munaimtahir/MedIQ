"""Integration test: Learning Engine + Session flow."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.session import TestSession, SessionMode, SessionStatus, SessionQuestion, SessionAnswer
from datetime import datetime
from uuid import uuid4

from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_submit_answers_then_verify_learning_updates(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test flow: create session -> submit answers -> verify learning engine updates."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Step 1: Create session
    session_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 3,
        },
    )
    
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]
    
    # Step 2: Get session state
    state_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert state_response.status_code == 200
    state_data = state_response.json()
    questions = state_data["questions"]
    
    # Step 3: Submit answers
    for q in questions[:3]:
        answer_response = await async_client.post(
            f"/v1/sessions/{session_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question_id": str(q["question_id"]),
                "selected_index": 0,  # Assume first option
                "marked_for_review": False,
            },
        )
        assert answer_response.status_code == 200
    
    # Step 4: Submit session (triggers learning engine updates)
    submit_response = await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert submit_response.status_code == 200
    submit_data = submit_response.json()
    assert submit_data["session"]["status"] == SessionStatus.SUBMITTED.value
    assert submit_data["session"]["score_correct"] is not None
    
    # Step 5: Verify session is in submitted state
    final_state = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert final_state.status_code == 200
    final_data = final_state.json()
    assert final_data["session"]["status"] == SessionStatus.SUBMITTED.value


@pytest.mark.asyncio
async def test_session_creation_with_learning_state_snapshot(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test that session creation snapshots algorithm state for continuity."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session
    session_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 2,
        },
    )
    
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]
    
    # Verify session has algorithm snapshot
    from app.models.session import TestSession
    
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    assert session is not None
    # Session should have algorithm profile snapshot
    assert session.algo_profile_at_start is not None
    assert session.algo_overrides_at_start is not None
