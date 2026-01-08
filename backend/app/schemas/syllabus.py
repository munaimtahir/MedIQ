"""Schemas for syllabus (Years, Blocks, Themes)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Student Read Schemas
# ============================================================================


class YearResponse(BaseModel):
    """Year response for students (active only)."""

    id: int
    name: str
    order_no: int

    class Config:
        from_attributes = True


class BlockResponse(BaseModel):
    """Block response for students (active only)."""

    id: int
    year_id: int
    code: str
    name: str
    order_no: int

    class Config:
        from_attributes = True


class ThemeResponse(BaseModel):
    """Theme response for students (active only)."""

    id: int
    block_id: int
    title: str
    order_no: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Admin CRUD Schemas
# ============================================================================


class YearBase(BaseModel):
    """Base schema for year."""

    name: str = Field(..., min_length=1, max_length=100)
    order_no: int = Field(..., ge=1)
    is_active: bool = Field(default=True)


class YearCreate(YearBase):
    """Schema for creating a year."""

    pass


class YearUpdate(BaseModel):
    """Schema for updating a year."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    order_no: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class YearAdminResponse(YearBase):
    """Year response for admin (includes all fields)."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlockBase(BaseModel):
    """Base schema for block."""

    year_id: int
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    order_no: int = Field(..., ge=1)
    is_active: bool = Field(default=True)


class BlockCreate(BlockBase):
    """Schema for creating a block."""

    pass


class BlockUpdate(BaseModel):
    """Schema for updating a block."""

    year_id: Optional[int] = None
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    order_no: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class BlockAdminResponse(BlockBase):
    """Block response for admin (includes all fields)."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ThemeBase(BaseModel):
    """Base schema for theme."""

    block_id: int
    title: str = Field(..., min_length=1, max_length=200)
    order_no: int = Field(..., ge=1)
    description: Optional[str] = None
    is_active: bool = Field(default=True)


class ThemeCreate(ThemeBase):
    """Schema for creating a theme."""

    pass


class ThemeUpdate(BaseModel):
    """Schema for updating a theme."""

    block_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    order_no: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ThemeAdminResponse(ThemeBase):
    """Theme response for admin (includes all fields)."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Reorder Schemas
# ============================================================================


class ReorderBlocksRequest(BaseModel):
    """Request schema for reordering blocks."""

    ordered_block_ids: list[int] = Field(..., min_length=1)


class ReorderThemesRequest(BaseModel):
    """Request schema for reordering themes."""

    ordered_theme_ids: list[int] = Field(..., min_length=1)


# ============================================================================
# CSV Import/Export Schemas
# ============================================================================


class CSVImportResult(BaseModel):
    """Result schema for CSV import."""

    dry_run: bool
    accepted: int
    rejected: int
    created: int
    updated: int
    errors: list[dict] = Field(default_factory=list)


class CSVError(BaseModel):
    """Error entry in CSV import result."""

    row: int
    reason: str
    data: dict
