import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import AttemptAnswer, AttemptSession, Block, Question, Theme, User
from schemas import (
    AnswerSubmit,
    BlockResponse,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    ReviewResponse,
    SessionCreate,
    SessionResponse,
    ThemeResponse,
)
from seed import seed_database

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)


# Auto-seed if database is empty (skip in test mode)
def check_and_seed():
    # Skip seeding in test environment
    if os.getenv("ENV") == "test" or os.getenv("SKIP_SEED") == "true":
        return

    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            print("Database is empty, seeding...")
            seed_database()
            print("Database seeded successfully")
    except Exception as e:
        print(f"Error checking/seeding database: {e}")
    finally:
        db.close()


check_and_seed()

app = FastAPI(title="Medical Exam Platform API", version="1.0.0")

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_id(x_user_id: str | None = Header(None, alias="X-User-Id")) -> str:
    """Temporary auth: extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id


def get_user(db: Session, user_id: str) -> User:
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Seed endpoint (for development)
@app.post("/seed")
def seed():
    seed_database()
    return {"message": "Database seeded successfully"}


# ============ SYLLABUS ENDPOINTS ============


@app.get("/blocks", response_model=list[BlockResponse])
def get_blocks(year: int | None = None, db: Session = Depends(get_db)):
    """Get blocks, optionally filtered by year"""
    query = db.query(Block)
    if year:
        query = query.filter(Block.year == year)
    return query.all()


@app.get("/themes", response_model=list[ThemeResponse])
def get_themes(block_id: str | None = None, db: Session = Depends(get_db)):
    """Get themes, optionally filtered by block_id"""
    query = db.query(Theme)
    if block_id:
        query = query.filter(Theme.block_id == block_id)
    return query.all()


# ============ ADMIN QUESTION ENDPOINTS ============


@app.get("/admin/questions", response_model=list[QuestionResponse])
def list_questions(
    skip: int = 0,
    limit: int = 100,
    published: bool | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """List questions (admin only)"""
    user = get_user(db, user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(Question)
    if published is not None:
        query = query.filter(Question.is_published == published)
    return query.offset(skip).limit(limit).all()


@app.post("/admin/questions", response_model=QuestionResponse)
def create_question(
    question: QuestionCreate, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Create a new question (admin only)"""
    user = get_user(db, user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db_question = Question(**question.dict())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


@app.get("/admin/questions/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Get a question by ID (admin only)"""
    user = get_user(db, user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.put("/admin/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    question: QuestionUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Update a question (admin only)"""
    user = get_user(db, user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db_question = db.query(Question).filter(Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    update_data = question.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_question, key, value)

    db.commit()
    db.refresh(db_question)
    return db_question


@app.post("/admin/questions/{question_id}/publish")
def publish_question(
    question_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Publish a question (admin only)"""
    user = get_user(db, user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db_question = db.query(Question).filter(Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Validation: require tags before publishing
    if not db_question.tags:
        raise HTTPException(status_code=400, detail="Tags required before publishing")

    db_question.is_published = True
    db.commit()
    return {"message": "Question published", "question_id": question_id}


@app.post("/admin/questions/{question_id}/unpublish")
def unpublish_question(
    question_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Unpublish a question (admin only)"""
    user = get_user(db, user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db_question = db.query(Question).filter(Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    db_question.is_published = False
    db.commit()
    return {"message": "Question unpublished", "question_id": question_id}


# ============ STUDENT PRACTICE ENDPOINTS ============


@app.get("/questions", response_model=list[QuestionResponse])
def get_published_questions(
    theme_id: int | None = None,
    block_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get published questions (student access)"""
    query = db.query(Question).filter(Question.is_published)

    if theme_id:
        query = query.filter(Question.theme_id == theme_id)
    elif block_id:
        query = query.join(Theme).filter(Theme.block_id == block_id)

    return query.limit(limit).all()


@app.post("/sessions", response_model=SessionResponse)
def create_session(
    session_data: SessionCreate, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Create a practice session"""
    user = get_user(db, user_id)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required")

    # Get questions for the session
    query = db.query(Question).filter(Question.is_published)
    if session_data.theme_id:
        query = query.filter(Question.theme_id == session_data.theme_id)
    elif session_data.block_id:
        query = query.join(Theme).filter(Theme.block_id == session_data.block_id)

    questions = query.limit(session_data.question_count or 30).all()

    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")

    session = AttemptSession(
        user_id=user_id,
        question_count=len(questions),
        time_limit_minutes=session_data.time_limit_minutes or 60,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Store question IDs in session (simplified - in production, use a junction table)
    session.question_ids = [q.id for q in questions]
    db.commit()

    return session


@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Get a session by ID"""
    session = (
        db.query(AttemptSession)
        .filter(AttemptSession.id == session_id, AttemptSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/sessions/{session_id}/answer")
def submit_answer(
    session_id: int,
    answer: AnswerSubmit,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Submit an answer for a question in a session"""
    session = (
        db.query(AttemptSession)
        .filter(AttemptSession.id == session_id, AttemptSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_submitted:
        raise HTTPException(status_code=400, detail="Session already submitted")

    question = db.query(Question).filter(Question.id == answer.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if answer already exists
    existing = (
        db.query(AttemptAnswer)
        .filter(
            AttemptAnswer.session_id == session_id, AttemptAnswer.question_id == answer.question_id
        )
        .first()
    )

    is_correct = answer.selected_option_index == question.correct_option_index

    if existing:
        existing.selected_option_index = answer.selected_option_index
        existing.is_correct = is_correct
        existing.is_marked_for_review = answer.is_marked_for_review
    else:
        attempt_answer = AttemptAnswer(
            session_id=session_id,
            question_id=answer.question_id,
            selected_option_index=answer.selected_option_index,
            is_correct=is_correct,
            is_marked_for_review=answer.is_marked_for_review,
        )
        db.add(attempt_answer)

    db.commit()
    return {"message": "Answer submitted", "is_correct": is_correct}


@app.post("/sessions/{session_id}/submit")
def submit_session(
    session_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Submit a session (finalize)"""
    session = (
        db.query(AttemptSession)
        .filter(AttemptSession.id == session_id, AttemptSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_submitted:
        raise HTTPException(status_code=400, detail="Session already submitted")

    session.is_submitted = True
    db.commit()

    # Calculate score
    answers = db.query(AttemptAnswer).filter(AttemptAnswer.session_id == session_id).all()
    correct_count = sum(1 for a in answers if a.is_correct)
    total_count = len(answers)

    return {
        "message": "Session submitted",
        "score": correct_count,
        "total": total_count,
        "percentage": round((correct_count / total_count * 100) if total_count > 0 else 0, 2),
    }


@app.get("/sessions/{session_id}/review", response_model=ReviewResponse)
def get_session_review(
    session_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Get review data for a submitted session"""
    session = (
        db.query(AttemptSession)
        .filter(AttemptSession.id == session_id, AttemptSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.is_submitted:
        raise HTTPException(status_code=400, detail="Session not submitted yet")

    answers = db.query(AttemptAnswer).filter(AttemptAnswer.session_id == session_id).all()

    review_data = []
    for answer in answers:
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        review_data.append(
            {
                "question_id": question.id,
                "question_text": question.question_text,
                "options": question.options,
                "correct_option_index": question.correct_option_index,
                "selected_option_index": answer.selected_option_index,
                "is_correct": answer.is_correct,
                "explanation": question.explanation,
                "is_marked_for_review": answer.is_marked_for_review,
            }
        )

    correct_count = sum(1 for a in answers if a.is_correct)

    return {
        "session_id": session_id,
        "total_questions": len(review_data),
        "correct_count": correct_count,
        "incorrect_count": len(review_data) - correct_count,
        "score_percentage": round(
            (correct_count / len(review_data) * 100) if review_data else 0, 2
        ),
        "questions": review_data,
    }


@app.get("/")
def root():
    return {"message": "Medical Exam Platform API", "version": "1.0.0"}
