"""Integration test: CMS + Analytics flow."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.question_cms import Question, QuestionStatus
from tests.helpers.seed import create_test_admin, create_test_student


@pytest.mark.asyncio
async def test_create_publish_question_then_check_analytics(
    async_client: AsyncClient,
    db: Session,
    test_admin_user,
    test_user,
) -> None:
    """Test flow: create question -> publish -> check analytics."""
    admin_token = create_access_token(user_id=str(test_admin_user.id), role=test_admin_user.role)
    student_token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Step 1: Create question as admin
    create_response = await async_client.post(
        "/v1/admin/questions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "stem": "Integration test question",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "option_e": "E",
            "correct_index": 0,
            "year_id": 1,
            "block_id": 1,
            "theme_id": 1,
            "difficulty": "MEDIUM",
            "cognitive_level": "UNDERSTAND",
        },
    )
    
    assert create_response.status_code == 201
    question_data = create_response.json()
    question_id = question_data["id"]
    
    # Step 2: Submit for review
    submit_response = await async_client.post(
        f"/v1/admin/questions/{question_id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    assert submit_response.status_code == 200
    
    # Step 3: Approve
    approve_response = await async_client.post(
        f"/v1/admin/questions/{question_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    assert approve_response.status_code == 200
    
    # Step 4: Publish
    publish_response = await async_client.post(
        f"/v1/admin/questions/{question_id}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "source_book": "Test Book",
            "source_page": "p. 1",
        },
    )
    
    assert publish_response.status_code == 200
    
    # Step 5: Verify question is published
    get_response = await async_client.get(
        f"/v1/admin/questions/{question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    assert get_response.status_code == 200
    question = get_response.json()
    assert question["status"] == QuestionStatus.PUBLISHED.value
    
    # Step 6: Check analytics (should be accessible)
    analytics_response = await async_client.get(
        "/v1/analytics/overview",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    
    # Analytics should be accessible (may be empty)
    assert analytics_response.status_code == 200


@pytest.mark.asyncio
async def test_student_cannot_access_unpublished_question_in_session(
    async_client: AsyncClient,
    db: Session,
    test_admin_user,
    test_user,
) -> None:
    """Test that unpublished questions don't appear in sessions."""
    admin_token = create_access_token(user_id=str(test_admin_user.id), role=test_admin_user.role)
    student_token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create draft question (not published)
    create_response = await async_client.post(
        "/v1/admin/questions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "stem": "Draft question",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "option_e": "E",
            "correct_index": 0,
            "year_id": 1,
            "block_id": 1,
            "theme_id": 1,
        },
    )
    
    assert create_response.status_code == 201
    question_id = create_response.json()["id"]
    
    # Verify question is DRAFT
    get_response = await async_client.get(
        f"/v1/admin/questions/{question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.json()["status"] == QuestionStatus.DRAFT.value
    
    # Create session as student (should not include draft question)
    session_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 10,
        },
    )
    
    assert session_response.status_code == 200
    session_data = session_response.json()
    
    # Get session state
    state_response = await async_client.get(
        f"/v1/sessions/{session_data['session_id']}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    
    assert state_response.status_code == 200
    state_data = state_response.json()
    
    # Verify draft question is not in session
    question_ids = [q["question_id"] for q in state_data["questions"]]
    assert str(question_id) not in question_ids
