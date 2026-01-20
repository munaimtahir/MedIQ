"""Seed demo accounts for development."""

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole

logger = get_logger(__name__)


def seed_demo_accounts() -> None:
    """Seed demo accounts if enabled in dev environment."""
    if settings.ENV != "dev" or not settings.SEED_DEMO_ACCOUNTS:
        logger.info("Demo account seeding skipped (ENV != dev or SEED_DEMO_ACCOUNTS=false)")
        return

    db = SessionLocal()
    try:
        # Check if accounts already exist
        admin_exists = db.query(User).filter(User.email == "admin@example.com").first()
        student_exists = db.query(User).filter(User.email == "student@example.com").first()

        if admin_exists and student_exists:
            logger.info("Demo accounts already exist, skipping seed")
            return

        # Create admin account
        if not admin_exists:
            admin = User(
                name="Admin User",
                email="admin@example.com",
                password_hash=hash_password("Admin123!"),
                role=UserRole.ADMIN.value,
                onboarding_completed=True,
                is_active=True,
                email_verified=True,
            )
            db.add(admin)
            logger.info("Created demo admin account: admin@example.com / Admin123!")

        # Create student account
        if not student_exists:
            student = User(
                name="Student User",
                email="student@example.com",
                password_hash=hash_password("Student123!"),
                role=UserRole.STUDENT.value,
                onboarding_completed=False,
                is_active=True,
                email_verified=False,
            )
            db.add(student)
            logger.info("Created demo student account: student@example.com / Student123!")

        # Create reviewer account
        reviewer_exists = db.query(User).filter(User.email == "reviewer@example.com").first()
        if not reviewer_exists:
            reviewer = User(
                name="Reviewer User",
                email="reviewer@example.com",
                password_hash=hash_password("Reviewer123!"),
                role=UserRole.REVIEWER.value,
                onboarding_completed=True,
                is_active=True,
                email_verified=True,
            )
            db.add(reviewer)
            logger.info("Created demo reviewer account: reviewer@example.com / Reviewer123!")

        db.commit()
        logger.info("Demo accounts seeded successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding demo accounts: {e}", exc_info=True)
        raise
    finally:
        db.close()
