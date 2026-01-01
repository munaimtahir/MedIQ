"""Onboarding and user profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.academic import (
    AcademicBlock,
    AcademicSubject,
    AcademicYear,
    UserBlock,
    UserProfile,
    UserSubject,
)
from app.models.user import User, UserRole
from app.schemas.academic import (
    OnboardingBlockOption,
    OnboardingOptionsResponse,
    OnboardingRequest,
    OnboardingStatusResponse,
    OnboardingSubjectOption,
    OnboardingYearOption,
    UserProfileBlockResponse,
    UserProfileResponse,
    UserProfileSubjectResponse,
    UserProfileYearResponse,
)

router = APIRouter(tags=["Onboarding"])


@router.get(
    "/onboarding/options",
    response_model=OnboardingOptionsResponse,
    summary="Get onboarding options",
    description="Get available academic years, blocks, and subjects for onboarding selection.",
)
async def get_onboarding_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingOptionsResponse:
    """
    Retrieve all active academic years with their blocks and subjects.
    Only returns active items, sorted by sort_order.
    """
    # Query all active years with their relationships
    years = (
        db.query(AcademicYear)
        .filter(AcademicYear.is_active == True)  # noqa: E712
        .options(
            joinedload(AcademicYear.blocks),
            joinedload(AcademicYear.subjects),
        )
        .order_by(AcademicYear.sort_order)
        .all()
    )
    
    result_years = []
    for year in years:
        # Filter and sort active blocks
        active_blocks = sorted(
            [b for b in year.blocks if b.is_active],
            key=lambda x: x.sort_order,
        )
        # Filter and sort active subjects
        active_subjects = sorted(
            [s for s in year.subjects if s.is_active],
            key=lambda x: x.sort_order,
        )
        
        result_years.append(
            OnboardingYearOption(
                id=year.id,
                slug=year.slug,
                display_name=year.display_name,
                blocks=[
                    OnboardingBlockOption(
                        id=b.id,
                        code=b.code,
                        display_name=b.display_name,
                    )
                    for b in active_blocks
                ],
                subjects=[
                    OnboardingSubjectOption(
                        id=s.id,
                        code=s.code,
                        display_name=s.display_name,
                    )
                    for s in active_subjects
                ],
            )
        )
    
    return OnboardingOptionsResponse(years=result_years)


@router.post(
    "/users/me/onboarding",
    response_model=OnboardingStatusResponse,
    summary="Complete onboarding",
    description="Submit onboarding selections (year, blocks, and optionally subjects).",
)
async def complete_onboarding(
    request: OnboardingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingStatusResponse:
    """
    Complete the onboarding process by selecting year, blocks, and optionally subjects.
    
    Validation:
    - Year must exist and be active
    - All blocks must belong to the selected year and be active
    - All subjects (if provided) must belong to the selected year and be active
    
    This is idempotent - calling again replaces existing selections.
    """
    # Validate year exists and is active
    year = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.id == request.year_id,
            AcademicYear.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive academic year selected",
        )
    
    # Validate blocks belong to selected year and are active
    blocks = (
        db.query(AcademicBlock)
        .filter(
            AcademicBlock.id.in_(request.block_ids),
            AcademicBlock.year_id == request.year_id,
            AcademicBlock.is_active == True,  # noqa: E712
        )
        .all()
    )
    if len(blocks) != len(request.block_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more blocks are invalid, inactive, or do not belong to the selected year",
        )
    
    # Validate subjects if provided
    if request.subject_ids:
        subjects = (
            db.query(AcademicSubject)
            .filter(
                AcademicSubject.id.in_(request.subject_ids),
                AcademicSubject.year_id == request.year_id,
                AcademicSubject.is_active == True,  # noqa: E712
            )
            .all()
        )
        if len(subjects) != len(request.subject_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more subjects are invalid, inactive, or do not belong to the selected year",
            )
    
    # Get or create user profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    # Update profile
    profile.selected_year_id = request.year_id
    profile.onboarding_completed = True
    
    # Clear existing block selections
    db.query(UserBlock).filter(UserBlock.user_id == current_user.id).delete()
    
    # Add new block selections
    for block_id in request.block_ids:
        db.add(UserBlock(user_id=current_user.id, block_id=block_id))
    
    # Clear existing subject selections
    db.query(UserSubject).filter(UserSubject.user_id == current_user.id).delete()
    
    # Add new subject selections if provided
    if request.subject_ids:
        for subject_id in request.subject_ids:
            db.add(UserSubject(user_id=current_user.id, subject_id=subject_id))
    
    # Also update the onboarding_completed flag on the User model
    current_user.onboarding_completed = True
    
    db.commit()
    
    return OnboardingStatusResponse(
        status="success",
        message="Onboarding completed successfully",
    )


@router.get(
    "/users/me/profile",
    response_model=UserProfileResponse,
    summary="Get user profile",
    description="Get the current user's onboarding profile and selections.",
)
async def get_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Retrieve the current user's profile including:
    - Onboarding completion status
    - Selected academic year
    - Selected blocks
    - Selected subjects
    """
    profile = (
        db.query(UserProfile)
        .options(
            joinedload(UserProfile.selected_year),
            joinedload(UserProfile.selected_blocks).joinedload(UserBlock.block),
            joinedload(UserProfile.selected_subjects).joinedload(UserSubject.subject),
        )
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    
    if not profile:
        # Return empty profile if not yet created
        return UserProfileResponse(
            user_id=current_user.id,
            onboarding_completed=current_user.onboarding_completed,
            selected_year=None,
            selected_blocks=[],
            selected_subjects=[],
            created_at=current_user.created_at,
            updated_at=None,
        )
    
    # Build response
    selected_year = None
    if profile.selected_year:
        selected_year = UserProfileYearResponse(
            id=profile.selected_year.id,
            slug=profile.selected_year.slug,
            display_name=profile.selected_year.display_name,
        )
    
    selected_blocks = [
        UserProfileBlockResponse(
            id=ub.block.id,
            code=ub.block.code,
            display_name=ub.block.display_name,
        )
        for ub in profile.selected_blocks
        if ub.block
    ]
    
    selected_subjects = [
        UserProfileSubjectResponse(
            id=us.subject.id,
            code=us.subject.code,
            display_name=us.subject.display_name,
        )
        for us in profile.selected_subjects
        if us.subject
    ]
    
    return UserProfileResponse(
        user_id=profile.user_id,
        onboarding_completed=profile.onboarding_completed,
        selected_year=selected_year,
        selected_blocks=selected_blocks,
        selected_subjects=selected_subjects,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
