from datetime import datetime

from pydantic import BaseModel, Field, validator

# ============ SYLLABUS SCHEMAS ============


class BlockResponse(BaseModel):
    id: str
    name: str
    year: int
    description: str | None = None

    class Config:
        from_attributes = True


class ThemeResponse(BaseModel):
    id: int
    block_id: str
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


# ============ QUESTION SCHEMAS ============


class QuestionResponse(BaseModel):
    id: int
    theme_id: int
    question_text: str
    options: list[str]
    correct_option_index: int
    explanation: str | None = None
    tags: list[str] | None = None
    difficulty: str | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    theme_id: int
    question_text: str
    options: list[str] = Field(..., min_items=5, max_items=5)
    correct_option_index: int = Field(..., ge=0, le=4)
    explanation: str | None = None
    tags: list[str] | None = None
    difficulty: str | None = None

    @validator("options")
    def validate_options(cls, v):
        if len(v) != 5:
            raise ValueError("Must have exactly 5 options")
        return v

    @validator("correct_option_index")
    def validate_correct_index(cls, v, values):
        if "options" in values and v >= len(values["options"]):
            raise ValueError("correct_option_index must be within options range")
        return v


class QuestionUpdate(BaseModel):
    theme_id: int | None = None
    question_text: str | None = None
    options: list[str] | None = Field(None, min_items=5, max_items=5)
    correct_option_index: int | None = Field(None, ge=0, le=4)
    explanation: str | None = None
    tags: list[str] | None = None
    difficulty: str | None = None
    is_published: bool | None = None


# ============ SESSION SCHEMAS ============


class SessionCreate(BaseModel):
    theme_id: int | None = None
    block_id: str | None = None
    question_count: int | None = Field(30, ge=1, le=100)
    time_limit_minutes: int | None = Field(60, ge=1)


class SessionResponse(BaseModel):
    id: int
    user_id: str
    question_count: int
    time_limit_minutes: int
    question_ids: list[int]
    is_submitted: bool
    started_at: datetime
    submitted_at: datetime | None = None

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: int
    selected_option_index: int = Field(..., ge=0, le=4)
    is_marked_for_review: bool = False


class ReviewResponse(BaseModel):
    session_id: int
    total_questions: int
    correct_count: int
    incorrect_count: int
    score_percentage: float
    questions: list[dict]
