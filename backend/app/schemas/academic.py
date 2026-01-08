"""Schemas for academic structure and onboarding."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Academic Structure Schemas
# ============================================================================


class AcademicBlockBase(BaseModel):
    """Base schema for academic block."""

    code: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)


class AcademicBlockCreate(AcademicBlockBase):
    """Schema for creating an academic block."""

    year_id: int


class AcademicBlockUpdate(BaseModel):
    """Schema for updating an academic block."""

    code: str | None = Field(None, min_length=1, max_length=50)
    display_name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = Field(None, ge=0)
    is_active: bool | None = None


class AcademicBlockResponse(AcademicBlockBase):
    """Response schema for academic block."""

    id: int
    year_id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AcademicSubjectBase(BaseModel):
    """Base schema for academic subject."""

    code: str | None = Field(None, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)


class AcademicSubjectCreate(AcademicSubjectBase):
    """Schema for creating an academic subject."""

    year_id: int


class AcademicSubjectUpdate(BaseModel):
    """Schema for updating an academic subject."""

    code: str | None = Field(None, max_length=50)
    display_name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = Field(None, ge=0)
    is_active: bool | None = None


class AcademicSubjectResponse(AcademicSubjectBase):
    """Response schema for academic subject."""

    id: int
    year_id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AcademicYearBase(BaseModel):
    """Base schema for academic year."""

    slug: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)


class AcademicYearCreate(AcademicYearBase):
    """Schema for creating an academic year."""

    pass


class AcademicYearUpdate(BaseModel):
    """Schema for updating an academic year."""

    slug: str | None = Field(None, min_length=1, max_length=50)
    display_name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = Field(None, ge=0)
    is_active: bool | None = None


class AcademicYearResponse(AcademicYearBase):
    """Response schema for academic year (without nested data)."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AcademicYearWithRelations(AcademicYearResponse):
    """Response schema for academic year with blocks and subjects."""

    blocks: list[AcademicBlockResponse] = []
    subjects: list[AcademicSubjectResponse] = []


# ============================================================================
# Onboarding Schemas
# ============================================================================


class OnboardingBlockOption(BaseModel):
    """Block option for onboarding."""

    id: int
    code: str
    display_name: str

    class Config:
        from_attributes = True


class OnboardingSubjectOption(BaseModel):
    """Subject option for onboarding."""

    id: int
    code: str | None
    display_name: str

    class Config:
        from_attributes = True


class OnboardingYearOption(BaseModel):
    """Year option for onboarding with blocks and subjects."""

    id: int
    slug: str
    display_name: str
    blocks: list[OnboardingBlockOption]
    subjects: list[OnboardingSubjectOption]


class OnboardingOptionsResponse(BaseModel):
    """Response schema for onboarding options."""

    years: list[OnboardingYearOption]


class OnboardingRequest(BaseModel):
    """Request schema for submitting onboarding selections."""

    year_id: int
    block_ids: list[int] = Field(..., min_length=1)
    subject_ids: list[int] | None = None


class OnboardingStatusResponse(BaseModel):
    """Response schema for onboarding status."""

    status: str
    message: str


# ============================================================================
# User Profile Schemas
# ============================================================================


class UserProfileBlockResponse(BaseModel):
    """Block in user profile response."""

    id: int
    code: str
    display_name: str

    class Config:
        from_attributes = True


class UserProfileSubjectResponse(BaseModel):
    """Subject in user profile response."""

    id: int
    code: str | None
    display_name: str

    class Config:
        from_attributes = True


class UserProfileYearResponse(BaseModel):
    """Year in user profile response."""

    id: int
    slug: str
    display_name: str

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """Response schema for user profile."""

    user_id: UUID
    onboarding_completed: bool
    selected_year: UserProfileYearResponse | None = None
    selected_blocks: list[UserProfileBlockResponse] = []
    selected_subjects: list[UserProfileSubjectResponse] = []
    created_at: datetime
    updated_at: datetime | None = None


# ============================================================================
# Admin Academic Structure Schemas
# ============================================================================


class AcademicStructureResponse(BaseModel):
    """Full academic structure response for admin."""

    years: list[AcademicYearWithRelations]
