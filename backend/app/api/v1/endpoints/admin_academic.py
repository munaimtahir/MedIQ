"""Admin endpoints for managing academic structure."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.academic import AcademicBlock, AcademicSubject, AcademicYear
from app.models.user import User, UserRole
from app.schemas.academic import (
    AcademicBlockCreate,
    AcademicBlockResponse,
    AcademicBlockUpdate,
    AcademicStructureResponse,
    AcademicSubjectCreate,
    AcademicSubjectResponse,
    AcademicSubjectUpdate,
    AcademicYearCreate,
    AcademicYearResponse,
    AcademicYearUpdate,
    AcademicYearWithRelations,
)

router = APIRouter(prefix="/admin/academic", tags=["Admin - Academic Structure"])


# ============================================================================
# Academic Structure Overview
# ============================================================================


@router.get(
    "/structure",
    response_model=AcademicStructureResponse,
    summary="Get full academic structure",
    description="Get all academic years with their blocks and subjects (admin view).",
)
async def get_academic_structure(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> AcademicStructureResponse:
    """
    Retrieve the complete academic structure including all years, blocks, and subjects.
    Unlike the onboarding endpoint, this includes inactive items for admin management.
    """
    years = (
        db.query(AcademicYear)
        .options(
            joinedload(AcademicYear.blocks),
            joinedload(AcademicYear.subjects),
        )
        .order_by(AcademicYear.sort_order)
        .all()
    )
    
    result_years = []
    for year in years:
        sorted_blocks = sorted(year.blocks, key=lambda x: x.sort_order)
        sorted_subjects = sorted(year.subjects, key=lambda x: x.sort_order)
        
        result_years.append(
            AcademicYearWithRelations(
                id=year.id,
                slug=year.slug,
                display_name=year.display_name,
                sort_order=year.sort_order,
                is_active=year.is_active,
                created_at=year.created_at,
                updated_at=year.updated_at,
                blocks=[
                    AcademicBlockResponse(
                        id=b.id,
                        year_id=b.year_id,
                        code=b.code,
                        display_name=b.display_name,
                        sort_order=b.sort_order,
                        is_active=b.is_active,
                        created_at=b.created_at,
                        updated_at=b.updated_at,
                    )
                    for b in sorted_blocks
                ],
                subjects=[
                    AcademicSubjectResponse(
                        id=s.id,
                        year_id=s.year_id,
                        code=s.code,
                        display_name=s.display_name,
                        sort_order=s.sort_order,
                        is_active=s.is_active,
                        created_at=s.created_at,
                        updated_at=s.updated_at,
                    )
                    for s in sorted_subjects
                ],
            )
        )
    
    return AcademicStructureResponse(years=result_years)


# ============================================================================
# Academic Year Management
# ============================================================================


@router.post(
    "/year",
    response_model=AcademicYearResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create academic year",
    description="Create a new academic year.",
)
async def create_academic_year(
    request: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AcademicYearResponse:
    """Create a new academic year."""
    year = AcademicYear(
        slug=request.slug,
        display_name=request.display_name,
        sort_order=request.sort_order,
        is_active=request.is_active,
    )
    
    try:
        db.add(year)
        db.commit()
        db.refresh(year)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Academic year with slug '{request.slug}' already exists",
        )
    
    return AcademicYearResponse.model_validate(year)


@router.put(
    "/year/{year_id}",
    response_model=AcademicYearResponse,
    summary="Update academic year",
    description="Update an existing academic year.",
)
async def update_academic_year(
    year_id: int,
    request: AcademicYearUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AcademicYearResponse:
    """Update an existing academic year."""
    year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic year not found",
        )
    
    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(year, field, value)
    
    try:
        db.commit()
        db.refresh(year)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Academic year with slug '{request.slug}' already exists",
        )
    
    return AcademicYearResponse.model_validate(year)


# ============================================================================
# Academic Block Management
# ============================================================================


@router.post(
    "/block",
    response_model=AcademicBlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create academic block",
    description="Create a new academic block within a year.",
)
async def create_academic_block(
    request: AcademicBlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AcademicBlockResponse:
    """Create a new academic block."""
    # Verify year exists
    year = db.query(AcademicYear).filter(AcademicYear.id == request.year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic year not found",
        )
    
    block = AcademicBlock(
        year_id=request.year_id,
        code=request.code,
        display_name=request.display_name,
        sort_order=request.sort_order,
        is_active=request.is_active,
    )
    
    try:
        db.add(block)
        db.commit()
        db.refresh(block)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Block with code '{request.code}' already exists in this year",
        )
    
    return AcademicBlockResponse.model_validate(block)


@router.put(
    "/block/{block_id}",
    response_model=AcademicBlockResponse,
    summary="Update academic block",
    description="Update an existing academic block.",
)
async def update_academic_block(
    block_id: int,
    request: AcademicBlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AcademicBlockResponse:
    """Update an existing academic block."""
    block = db.query(AcademicBlock).filter(AcademicBlock.id == block_id).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic block not found",
        )
    
    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(block, field, value)
    
    try:
        db.commit()
        db.refresh(block)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Block with code '{request.code}' already exists in this year",
        )
    
    return AcademicBlockResponse.model_validate(block)


# ============================================================================
# Academic Subject Management
# ============================================================================


@router.post(
    "/subject",
    response_model=AcademicSubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create academic subject",
    description="Create a new academic subject within a year.",
)
async def create_academic_subject(
    request: AcademicSubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AcademicSubjectResponse:
    """Create a new academic subject."""
    # Verify year exists
    year = db.query(AcademicYear).filter(AcademicYear.id == request.year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic year not found",
        )
    
    subject = AcademicSubject(
        year_id=request.year_id,
        code=request.code,
        display_name=request.display_name,
        sort_order=request.sort_order,
        is_active=request.is_active,
    )
    
    try:
        db.add(subject)
        db.commit()
        db.refresh(subject)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subject '{request.display_name}' already exists in this year",
        )
    
    return AcademicSubjectResponse.model_validate(subject)


@router.put(
    "/subject/{subject_id}",
    response_model=AcademicSubjectResponse,
    summary="Update academic subject",
    description="Update an existing academic subject.",
)
async def update_academic_subject(
    subject_id: int,
    request: AcademicSubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> AcademicSubjectResponse:
    """Update an existing academic subject."""
    subject = db.query(AcademicSubject).filter(AcademicSubject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic subject not found",
        )
    
    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subject, field, value)
    
    try:
        db.commit()
        db.refresh(subject)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subject '{request.display_name}' already exists in this year",
        )
    
    return AcademicSubjectResponse.model_validate(subject)


# ============================================================================
# Seed Endpoint (for initial setup)
# ============================================================================


@router.post(
    "/seed",
    summary="Seed academic structure",
    description="Seed initial academic structure data (Pakistan MBBS curriculum).",
)
async def seed_academic_structure_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    """Seed the academic structure with initial data."""
    from app.core.seed_academic import seed_academic_structure
    
    result = seed_academic_structure(db)
    return result
