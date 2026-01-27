"""Test seed helpers for creating test data."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole


def create_test_user(
    db: Session,
    email: str | None = None,
    password: str = "TestPass123!",
    role: UserRole = UserRole.STUDENT,
    email_verified: bool = True,
    is_active: bool = True,
    **kwargs: Any,
) -> User:
    """
    Create a test user with deterministic defaults.
    
    Args:
        db: Database session
        email: User email (defaults to role-based email)
        password: Plain password (will be hashed)
        role: User role
        email_verified: Whether email is verified
        is_active: Whether user is active
        **kwargs: Additional user attributes
    
    Returns:
        Created User instance
    """
    if email is None:
        user_id = uuid.uuid4()
        email = f"test_{role.value.lower()}_{user_id.hex[:8]}@test.example.com"
    
    user = User(
        id=kwargs.pop("id", uuid.uuid4()),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        role=role.value,
        email_verified=email_verified,
        is_active=is_active,
        onboarding_completed=True,
        full_name=kwargs.pop("full_name", f"Test {role.value}"),
        **kwargs,
    )
    db.add(user)
    db.flush()
    return user


def create_test_admin(
    db: Session,
    email: str | None = None,
    password: str = "AdminPass123!",
    **kwargs: Any,
) -> User:
    """Create a test admin user."""
    return create_test_user(
        db,
        email=email,
        password=password,
        role=UserRole.ADMIN,
        **kwargs,
    )


def create_test_student(
    db: Session,
    email: str | None = None,
    password: str = "StudentPass123!",
    **kwargs: Any,
) -> User:
    """Create a test student user."""
    return create_test_user(
        db,
        email=email,
        password=password,
        role=UserRole.STUDENT,
        **kwargs,
    )


def create_test_reviewer(
    db: Session,
    email: str | None = None,
    password: str = "ReviewerPass123!",
    **kwargs: Any,
) -> User:
    """Create a test reviewer user."""
    return create_test_user(
        db,
        email=email,
        password=password,
        role=UserRole.REVIEWER,
        **kwargs,
    )
