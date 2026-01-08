"""Script to clear all student user data from the database.

This script deletes all users with role='STUDENT' and their related data.
Related data (sessions, tokens, etc.) will be automatically deleted due to
cascade relationships.

Usage:
    python -m app.scripts.clear_students
    or
    python scripts/clear_students.py
"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)


def clear_students():
    """Delete all student users from the database using raw SQL."""
    db = SessionLocal()
    try:
        # Count students before deletion using raw SQL
        result = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'STUDENT'"))
        student_count = result.scalar()

        if student_count == 0:
            logger.info("No student users found in database.")
            print("No student users found in database.")
            return

        logger.info(f"Found {student_count} student user(s) to delete.")
        print(f"Found {student_count} student user(s) to delete.")

        # Delete all students using raw SQL (cascade will handle related data)
        result = db.execute(text("DELETE FROM users WHERE role = 'STUDENT'"))
        deleted_count = result.rowcount
        db.commit()

        logger.info(f"Successfully deleted {deleted_count} student user(s) and their related data.")
        print(f"Successfully deleted {deleted_count} student user(s) and their related data.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing students: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Clearing all student users from database...")
    try:
        clear_students()
        print("✓ Successfully cleared all student users.")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
