"""Student endpoints for reading syllabus (Years, Blocks, Themes)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.syllabus import Block, Theme, Year
from app.models.user import User
from app.schemas.syllabus import BlockResponse, ThemeResponse, YearResponse

router = APIRouter(prefix="/syllabus", tags=["Syllabus"])


@router.get(
    "/years",
    response_model=list[YearResponse],
    summary="Get active years",
    description="Get all active years ordered by order_no.",
)
async def get_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[YearResponse]:
    """Get all active years ordered by order_no."""
    years = db.query(Year).filter(Year.is_active.is_(True)).order_by(Year.order_no).all()
    return [YearResponse.model_validate(year) for year in years]


@router.get(
    "/blocks",
    response_model=list[BlockResponse],
    summary="Get blocks by year",
    description="Get active blocks for a specific year, ordered by order_no.",
)
async def get_blocks(
    year: str = Query(..., description="Year name or year ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BlockResponse]:
    """
    Get active blocks for a year.
    Year can be specified by name (e.g., "1st Year") or ID.
    """
    # Try to find year by ID first (if year is numeric)
    year_obj = None
    if year.isdigit():
        year_obj = db.query(Year).filter(Year.id == int(year), Year.is_active.is_(True)).first()

    # If not found by ID, try by name
    if not year_obj:
        year_obj = db.query(Year).filter(Year.name == year, Year.is_active.is_(True)).first()

    if not year_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Year '{year}' not found or inactive",
        )

    blocks = (
        db.query(Block)
        .filter(Block.year_id == year_obj.id, Block.is_active.is_(True))
        .order_by(Block.order_no)
        .all()
    )

    return [BlockResponse.model_validate(block) for block in blocks]


@router.get(
    "/themes",
    response_model=list[ThemeResponse],
    summary="Get themes by block",
    description="Get active themes for a specific block, ordered by order_no.",
)
async def get_themes(
    block_id: int = Query(..., description="Block ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ThemeResponse]:
    """Get active themes for a block."""
    # Verify block exists and is active
    block = db.query(Block).filter(Block.id == block_id, Block.is_active.is_(True)).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID {block_id} not found or inactive",
        )

    themes = (
        db.query(Theme)
        .filter(Theme.block_id == block_id, Theme.is_active.is_(True))
        .order_by(Theme.order_no)
        .all()
    )

    return [ThemeResponse.model_validate(theme) for theme in themes]
