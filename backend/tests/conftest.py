"""Pytest configuration and shared fixtures."""

import os
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.question_cms import Question, QuestionStatus
from app.models.session import SessionStatus, TestSession
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole

# Use test database URL if available, otherwise use PostgreSQL from env
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://exam_user:change_me@localhost:5432/exam_platform"),
)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a test database session with transaction rollback."""
    from app.db.engine import engine

    # Use a dedicated connection + outer transaction, and wrap each test in a SAVEPOINT.
    # This allows application code to call session.commit() without breaking teardown.
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, transaction) -> None:  # type: ignore[no-redef]
        # When the nested transaction ends (via commit/rollback), start a new SAVEPOINT
        # so the session remains usable for the rest of the test.
        if transaction.nested and not transaction._parent.nested:  # noqa: SLF001
            sess.begin_nested()

    try:
        # Ensure test data exists (year, block, theme)
        # Check if tables exist first (migrations might not have run for individual tests)
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "years" in tables:
            try:
                year = session.query(Year).filter(Year.id == 1).first()
                if not year:
                    year = Year(id=1, name="1st Year", order_no=1, is_active=True)
                    session.add(year)
                    session.flush()
            except Exception:
                # Table might not be fully initialized, skip
                pass

            if "blocks" in tables:
                try:
                    block = session.query(Block).filter(Block.id == 1).first()
                    if not block:
                        block = Block(id=1, year_id=1, code="A", name="Test Block", order_no=1, is_active=True)
                        session.add(block)
                        session.flush()
                except Exception:
                    # Table might not be fully initialized, skip
                    pass

                if "themes" in tables:
                    try:
                        theme = session.query(Theme).filter(Theme.id == 1).first()
                        if not theme:
                            theme = Theme(id=1, block_id=1, title="Test Theme", order_no=1, is_active=True)
                            session.add(theme)
                            session.flush()
                    except Exception:
                        # Table might not be fully initialized, skip
                        pass

        yield session
    finally:
        # Rollback transaction to clean up test data
        trans.rollback()
        session.close()
        connection.close()


@pytest.fixture
def test_user(db) -> User:
    """Create a test student user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        password_hash=hash_password("Test123!"),
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
        onboarding_completed=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def test_admin_user(db) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        full_name="Test Admin",
        password_hash=hash_password("Admin123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
        email_verified=True,
        onboarding_completed=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def published_questions(db, test_admin_user) -> list[Question]:
    """Create 10 published test questions (from seed data pattern)."""
    # Ensure year, block, theme exist (should be created by db fixture)
    year = db.query(Year).filter(Year.id == 1).first()
    block = db.query(Block).filter(Block.id == 1).first()
    theme = db.query(Theme).filter(Theme.id == 1).first()

    if not year or not block or not theme:
        raise ValueError("Year, block, and theme must exist (created by db fixture)")

    # Check if questions already exist (from seed)
    existing = db.query(Question).filter(Question.external_id.like("TEST-MCQ-%")).all()
    if len(existing) >= 10:
        return existing[:10]

    # Create 10 questions if not enough exist
    questions = []
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

    for i, (stem, options, correct_idx) in enumerate(zip(mcq_stems, mcq_options, correct_indices), 1):
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
            created_by=test_admin_user.id,
        )
        db.add(question)
        questions.append(question)

    db.flush()
    return questions


@pytest.fixture
def test_session(db, test_user, published_questions) -> TestSession:
    """Create a test session with questions."""
    from datetime import datetime, timedelta

    session = TestSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        year=1,
        blocks_json=["A"],
        total_questions=min(10, len(published_questions)),
        status=SessionStatus.ACTIVE,
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(session)
    db.flush()

    # Add questions to session
    from app.models.session import SessionQuestion

    for i, question in enumerate(published_questions[:10], 1):
        session_question = SessionQuestion(
            session_id=session.id,
            question_id=question.id,
            position=i,
        )
        db.add(session_question)

    db.flush()
    return session


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async test database session with transaction rollback."""
    # Convert postgresql:// or postgresql+psycopg2:// to postgresql+asyncpg:// for async
    if "postgresql+psycopg2://" in TEST_DATABASE_URL:
        async_url = TEST_DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif "postgresql://" in TEST_DATABASE_URL:
        async_url = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        async_url = TEST_DATABASE_URL
    async_engine = create_async_engine(
        async_url,
        pool_pre_ping=True,
        echo=False,
    )
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # Ensure test data exists (year, block, theme)
        from sqlalchemy import select

        year_result = await session.execute(select(Year).where(Year.id == 1))
        year = year_result.scalar_one_or_none()
        if not year:
            year = Year(id=1, name="1st Year", order_no=1, is_active=True)
            session.add(year)
            await session.flush()

        block_result = await session.execute(select(Block).where(Block.id == 1))
        block = block_result.scalar_one_or_none()
        if not block:
            block = Block(id=1, year_id=1, code="A", name="Test Block", order_no=1, is_active=True)
            session.add(block)
            await session.flush()

        theme_result = await session.execute(select(Theme).where(Theme.id == 1))
        theme = theme_result.scalar_one_or_none()
        if not theme:
            theme = Theme(id=1, block_id=1, title="Test Theme", order_no=1, is_active=True)
            session.add(theme)
            await session.flush()

        yield session
        await session.rollback()

    await async_engine.dispose()


@pytest.fixture
def client(db) -> TestClient:
    """Create a FastAPI test client with database dependency override."""
    from app.db.session import get_db
    
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Don't close the session, it's managed by the db fixture
    
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_client(client) -> TestClient:
    """Alias for client fixture for backward compatibility."""
    return client


@pytest.fixture
def admin_user(db) -> User:
    """Create an admin user for testing (alias for test_admin_user)."""
    return test_admin_user(db)
