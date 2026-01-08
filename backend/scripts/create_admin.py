#!/usr/bin/env python3
"""Script to create an admin user for development/testing."""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole

logger = get_logger(__name__)


def create_admin_user(
    email: str = "admin@example.com",
    password: str = "Admin123!",
    name: str = "Admin User",
) -> None:
    """Create an admin user in the database."""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            logger.warning(f"User with email {email} already exists.")
            if existing_user.role == UserRole.ADMIN.value:
                logger.info(f"Admin user already exists: {email}")
                print(f"\n✓ Admin user already exists!")
                print(f"  Email: {email}")
                print(f"  Password: (use existing password)")
                return
            else:
                # Update existing user to admin
                existing_user.role = UserRole.ADMIN.value
                existing_user.password_hash = hash_password(password)
                existing_user.name = name
                existing_user.is_active = True
                existing_user.email_verified = True
                existing_user.onboarding_completed = True
                db.commit()
                logger.info(f"Updated user {email} to admin role")
                print(f"\n✓ Updated user to admin!")
                print(f"  Email: {email}")
                print(f"  Password: {password}")
                return

        # Create new admin user
        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            onboarding_completed=True,
            is_active=True,
            email_verified=True,
        )
        db.add(admin)
        db.commit()
        logger.info(f"Created admin user: {email}")
        print(f"\n✓ Admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"  Name: {name}")
        print(f"\nYou can now log in with these credentials.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating admin user: {e}", exc_info=True)
        print(f"\n✗ Error creating admin user: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an admin user for development/testing")
    parser.add_argument(
        "--email",
        type=str,
        default="admin@example.com",
        help="Admin email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="Admin123!",
        help="Admin password (default: Admin123!)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="Admin User",
        help="Admin name (default: Admin User)",
    )

    args = parser.parse_args()

    print("Creating admin user...")
    create_admin_user(email=args.email, password=args.password, name=args.name)
