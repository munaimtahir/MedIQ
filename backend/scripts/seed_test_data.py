#!/usr/bin/env python3
"""Script to seed test data: 10 MCQs and 10 user profiles."""

import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.question_cms import Question, QuestionStatus
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole

logger = get_logger(__name__)


def seed_test_data() -> None:
    """Seed 10 MCQs and 10 user profiles."""
    db = SessionLocal()
    try:
        # Ensure year, block, theme exist
        year = db.query(Year).filter(Year.id == 1).first()
        if not year:
            year = Year(id=1, name="1st Year", order_no=1, is_active=True)
            db.add(year)
            db.flush()

        block = db.query(Block).filter(Block.id == 1).first()
        if not block:
            block = Block(id=1, year_id=1, code="A", name="Test Block", order_no=1, is_active=True)
            db.add(block)
            db.flush()

        theme = db.query(Theme).filter(Theme.id == 1).first()
        if not theme:
            theme = Theme(id=1, block_id=1, title="Test Theme", order_no=1, is_active=True)
            db.add(theme)
            db.flush()

        # Get or create a test admin user for question ownership
        admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin_user:
            admin_user = User(
                full_name="Test Admin",
                email="admin@example.com",
                password_hash=hash_password("Admin123!"),
                role=UserRole.ADMIN.value,
                onboarding_completed=True,
                is_active=True,
                email_verified=True,
            )
            db.add(admin_user)
            db.flush()

        # Seed 10 MCQs
        mcq_stems = [
            "What is the primary function of the heart?",
            "Which organ is responsible for filtering blood?",
            "What is the largest organ in the human body?",
            "Which blood type is known as the universal donor?",
            "What is the normal resting heart rate for adults?",
            "Which vitamin is produced by the skin when exposed to sunlight?",
            "What is the medical term for high blood pressure?",
            "Which part of the brain controls balance and coordination?",
            "What is the function of red blood cells?",
            "Which hormone regulates blood sugar levels?",
        ]

        mcq_options = [
            ["Pump blood", "Filter waste", "Produce hormones", "Digest food", "Store energy"],
            ["Heart", "Liver", "Kidneys", "Lungs", "Brain"],
            ["Heart", "Liver", "Skin", "Lungs", "Brain"],
            ["A", "B", "AB", "O", "None of the above"],
            ["40-60 bpm", "60-100 bpm", "100-120 bpm", "120-140 bpm", "140-160 bpm"],
            ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D", "Vitamin E"],
            ["Hypotension", "Hypertension", "Tachycardia", "Bradycardia", "Arrhythmia"],
            ["Cerebrum", "Cerebellum", "Brainstem", "Medulla", "Hypothalamus"],
            ["Carry oxygen", "Fight infection", "Clot blood", "Produce antibodies", "Remove waste"],
            ["Insulin", "Adrenaline", "Thyroxine", "Cortisol", "Estrogen"],
        ]

        correct_indices = [0, 2, 2, 3, 1, 3, 1, 1, 0, 0]

        questions_created = 0
        for i, (stem, options, correct_idx) in enumerate(zip(mcq_stems, mcq_options, correct_indices), 1):
            # Check if question already exists
            existing = db.query(Question).filter(Question.external_id == f"TEST-MCQ-{i:02d}").first()
            if existing:
                logger.info(f"Question TEST-MCQ-{i:02d} already exists, skipping")
                continue

            question = Question(
                external_id=f"TEST-MCQ-{i:02d}",
                stem=stem,
                option_a=options[0],
                option_b=options[1],
                option_c=options[2],
                option_d=options[3],
                option_e=options[4],
                correct_index=correct_idx,
                explanation_md=f"This is the correct answer because option {chr(65 + correct_idx)} is the most accurate.",
                status=QuestionStatus.PUBLISHED,
                year_id=1,
                block_id=1,
                theme_id=1,
                cognitive_level="UNDERSTAND",
                difficulty="MEDIUM",
                created_by=admin_user.id,
            )
            db.add(question)
            questions_created += 1

        db.flush()
        logger.info(f"Created {questions_created} MCQs")

        # Seed 10 user profiles
        user_profiles = [
            {"name": "Test Student 1", "email": "student1@test.com", "role": UserRole.STUDENT},
            {"name": "Test Student 2", "email": "student2@test.com", "role": UserRole.STUDENT},
            {"name": "Test Student 3", "email": "student3@test.com", "role": UserRole.STUDENT},
            {"name": "Test Student 4", "email": "student4@test.com", "role": UserRole.STUDENT},
            {"name": "Test Student 5", "email": "student5@test.com", "role": UserRole.STUDENT},
            {"name": "Test Student 6", "email": "student6@test.com", "role": UserRole.STUDENT},
            {"name": "Test Student 7", "email": "student7@test.com", "role": UserRole.STUDENT},
            {"name": "Test Student 8", "email": "student8@test.com", "role": UserRole.STUDENT},
            {"name": "Test Reviewer 1", "email": "reviewer1@test.com", "role": UserRole.REVIEWER},
            {"name": "Test Reviewer 2", "email": "reviewer2@test.com", "role": UserRole.REVIEWER},
        ]

        users_created = 0
        for profile in user_profiles:
            existing = db.query(User).filter(User.email == profile["email"]).first()
            if existing:
                logger.info(f"User {profile['email']} already exists, skipping")
                continue

            user = User(
                full_name=profile["name"],
                email=profile["email"],
                password_hash=hash_password("Test123!"),
                role=profile["role"].value,
                onboarding_completed=True,
                is_active=True,
                email_verified=True,
            )
            db.add(user)
            users_created += 1

        db.flush()
        logger.info(f"Created {users_created} user profiles")

        db.commit()
        print(f"\n✓ Test data seeded successfully!")
        print(f"  MCQs created: {questions_created}/10")
        print(f"  Users created: {users_created}/10")
        print("\nTest credentials:")
        print("  Students: student1@test.com through student8@test.com (password: Test123!)")
        print("  Reviewers: reviewer1@test.com, reviewer2@test.com (password: Test123!)")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding test data: {e}", exc_info=True)
        print(f"\n✗ Error seeding test data: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding test data (10 MCQs + 10 user profiles)...")
    seed_test_data()
