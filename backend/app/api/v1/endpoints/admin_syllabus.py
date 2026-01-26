"""Admin endpoints for managing syllabus (Years, Blocks, Themes)."""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cache.helpers import invalidate_syllabus_cache
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole
from app.schemas.syllabus import (
    BlockAdminResponse,
    BlockCreate,
    BlockUpdate,
    CSVImportResult,
    ReorderBlocksRequest,
    ReorderThemesRequest,
    ThemeAdminResponse,
    ThemeCreate,
    ThemeUpdate,
    YearAdminResponse,
    YearCreate,
    YearUpdate,
)

router = APIRouter(prefix="/admin/syllabus", tags=["Admin - Syllabus"])


# ============================================================================
# Seed Endpoint
# ============================================================================


@router.post(
    "/seed",
    summary="Seed syllabus structure",
    description="Seed default years and blocks (idempotent - only creates if missing).",
)
async def seed_syllabus_structure_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    """Seed the syllabus structure with default years and blocks."""
    from app.core.seed_syllabus import seed_syllabus_structure

    result = seed_syllabus_structure(db)
    invalidate_syllabus_cache()
    return result


# ============================================================================
# Years CRUD
# ============================================================================


@router.get(
    "/years",
    response_model=list[YearAdminResponse],
    summary="List all years",
    description="Get all years (including inactive) for admin management, ordered by order_no.",
)
async def list_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> list[YearAdminResponse]:
    """Get all years (admin view - includes inactive)."""
    years = db.query(Year).order_by(Year.order_no).all()
    return [YearAdminResponse.model_validate(year) for year in years]


@router.post(
    "/years",
    response_model=YearAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create year",
    description="Create a new academic year.",
)
async def create_year(
    request: YearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> YearAdminResponse:
    """Create a new year."""
    year = Year(
        name=request.name,
        order_no=request.order_no,
        is_active=request.is_active,
    )

    try:
        db.add(year)
        db.commit()
        db.refresh(year)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Year with name '{request.name}' already exists",
        ) from e

    return YearAdminResponse.model_validate(year)


@router.put(
    "/years/{year_id}",
    response_model=YearAdminResponse,
    summary="Update year",
    description="Update an existing year.",
)
async def update_year(
    year_id: int,
    request: YearUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> YearAdminResponse:
    """Update an existing year."""
    year = db.query(Year).filter(Year.id == year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Year not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(year, field, value)

    try:
        db.commit()
        db.refresh(year)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Year with name '{request.name}' already exists",
        ) from e

    invalidate_syllabus_cache()
    return YearAdminResponse.model_validate(year)


@router.post(
    "/years/{year_id}/disable",
    response_model=YearAdminResponse,
    summary="Disable year",
    description="Soft disable a year (sets is_active=false).",
)
async def disable_year(
    year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> YearAdminResponse:
    """Disable a year."""
    year = db.query(Year).filter(Year.id == year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Year not found",
        )

    year.is_active = False
    db.commit()
    db.refresh(year)

    invalidate_syllabus_cache()
    return YearAdminResponse.model_validate(year)


@router.post(
    "/years/{year_id}/enable",
    response_model=YearAdminResponse,
    summary="Enable year",
    description="Re-enable a year (sets is_active=true).",
)
async def enable_year(
    year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> YearAdminResponse:
    """Enable a year."""
    year = db.query(Year).filter(Year.id == year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Year not found",
        )

    year.is_active = True
    db.commit()
    db.refresh(year)

    invalidate_syllabus_cache()
    return YearAdminResponse.model_validate(year)


# ============================================================================
# Blocks CRUD
# ============================================================================


@router.get(
    "/years/{year_id}/blocks",
    response_model=list[BlockAdminResponse],
    summary="Get blocks for year",
    description="Get all blocks (including inactive) for a specific year, ordered by order_no.",
)
async def get_blocks_for_year(
    year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> list[BlockAdminResponse]:
    """Get all blocks for a year (admin view - includes inactive)."""
    # Verify year exists
    year = db.query(Year).filter(Year.id == year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Year not found",
        )

    blocks = db.query(Block).filter(Block.year_id == year_id).order_by(Block.order_no).all()

    return [BlockAdminResponse.model_validate(block) for block in blocks]


@router.post(
    "/blocks",
    response_model=BlockAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create block",
    description="Create a new block within a year.",
)
async def create_block(
    request: BlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> BlockAdminResponse:
    """Create a new block."""
    # Verify year exists
    year = db.query(Year).filter(Year.id == request.year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Year not found",
        )

    block = Block(
        year_id=request.year_id,
        code=request.code,
        name=request.name,
        order_no=request.order_no,
        is_active=request.is_active,
    )

    try:
        db.add(block)
        db.commit()
        db.refresh(block)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Block with code '{request.code}' already exists in this year",
        ) from e

    invalidate_syllabus_cache()
    return BlockAdminResponse.model_validate(block)


@router.put(
    "/blocks/{block_id}",
    response_model=BlockAdminResponse,
    summary="Update block",
    description="Update an existing block.",
)
async def update_block(
    block_id: int,
    request: BlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> BlockAdminResponse:
    """Update an existing block."""
    block = db.query(Block).filter(Block.id == block_id).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    # If year_id is being updated, verify new year exists
    if request.year_id is not None and request.year_id != block.year_id:
        year = db.query(Year).filter(Year.id == request.year_id).first()
        if not year:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Year not found",
            )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(block, field, value)

    try:
        db.commit()
        db.refresh(block)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Block with code '{request.code}' already exists in this year",
        ) from e

    invalidate_syllabus_cache()
    return BlockAdminResponse.model_validate(block)


@router.post(
    "/blocks/{block_id}/disable",
    response_model=BlockAdminResponse,
    summary="Disable block",
    description="Soft disable a block.",
)
async def disable_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> BlockAdminResponse:
    """Disable a block."""
    block = db.query(Block).filter(Block.id == block_id).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    block.is_active = False
    db.commit()
    db.refresh(block)

    invalidate_syllabus_cache()
    return BlockAdminResponse.model_validate(block)


@router.post(
    "/blocks/{block_id}/enable",
    response_model=BlockAdminResponse,
    summary="Enable block",
    description="Re-enable a block.",
)
async def enable_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> BlockAdminResponse:
    """Enable a block."""
    block = db.query(Block).filter(Block.id == block_id).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    block.is_active = True
    db.commit()
    db.refresh(block)

    invalidate_syllabus_cache()
    return BlockAdminResponse.model_validate(block)


# ============================================================================
# Themes CRUD
# ============================================================================


@router.get(
    "/blocks/{block_id}/themes",
    response_model=list[ThemeAdminResponse],
    summary="Get themes for block",
    description="Get all themes (including inactive) for a specific block, ordered by order_no.",
)
async def get_themes_for_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> list[ThemeAdminResponse]:
    """Get all themes for a block (admin view - includes inactive)."""
    # Verify block exists
    block = db.query(Block).filter(Block.id == block_id).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    themes = db.query(Theme).filter(Theme.block_id == block_id).order_by(Theme.order_no).all()

    return [ThemeAdminResponse.model_validate(theme) for theme in themes]


@router.post(
    "/themes",
    response_model=ThemeAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create theme",
    description="Create a new theme within a block.",
)
async def create_theme(
    request: ThemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> ThemeAdminResponse:
    """Create a new theme."""
    # Verify block exists
    block = db.query(Block).filter(Block.id == request.block_id).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    # Normalize title (trim whitespace, case-insensitive check)
    normalized_title = request.title.strip()

    theme = Theme(
        block_id=request.block_id,
        title=normalized_title,
        order_no=request.order_no,
        description=request.description,
        is_active=request.is_active,
    )

    try:
        db.add(theme)
        db.commit()
        db.refresh(theme)
    except IntegrityError as e:
        db.rollback()
        # Check if it's a duplicate title
        existing = (
            db.query(Theme)
            .filter(Theme.block_id == request.block_id, Theme.title.ilike(normalized_title))
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Theme with title '{normalized_title}' already exists in this block",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create theme",
        ) from e

    invalidate_syllabus_cache()
    return ThemeAdminResponse.model_validate(theme)


@router.put(
    "/themes/{theme_id}",
    response_model=ThemeAdminResponse,
    summary="Update theme",
    description="Update an existing theme.",
)
async def update_theme(
    theme_id: int,
    request: ThemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> ThemeAdminResponse:
    """Update an existing theme."""
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # If block_id is being updated, verify new block exists
    if request.block_id is not None and request.block_id != theme.block_id:
        block = db.query(Block).filter(Block.id == request.block_id).first()
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Block not found",
            )

    update_data = request.model_dump(exclude_unset=True)
    # Normalize title if provided
    if "title" in update_data and update_data["title"]:
        update_data["title"] = update_data["title"].strip()

    for field, value in update_data.items():
        setattr(theme, field, value)

    try:
        db.commit()
        db.refresh(theme)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Theme with title '{request.title}' already exists in this block",
        ) from e

    invalidate_syllabus_cache()
    return ThemeAdminResponse.model_validate(theme)


@router.post(
    "/themes/{theme_id}/disable",
    response_model=ThemeAdminResponse,
    summary="Disable theme",
    description="Soft disable a theme.",
)
async def disable_theme(
    theme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> ThemeAdminResponse:
    """Disable a theme."""
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    theme.is_active = False
    db.commit()
    db.refresh(theme)

    invalidate_syllabus_cache()
    return ThemeAdminResponse.model_validate(theme)


@router.post(
    "/themes/{theme_id}/enable",
    response_model=ThemeAdminResponse,
    summary="Enable theme",
    description="Re-enable a theme.",
)
async def enable_theme(
    theme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> ThemeAdminResponse:
    """Enable a theme."""
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    theme.is_active = True
    db.commit()
    db.refresh(theme)

    invalidate_syllabus_cache()
    return ThemeAdminResponse.model_validate(theme)


# ============================================================================
# Reorder Endpoints (Atomic)
# ============================================================================


@router.post(
    "/years/{year_id}/blocks/reorder",
    summary="Reorder blocks",
    description="Atomically reorder blocks within a year.",
)
async def reorder_blocks(
    year_id: int,
    request: ReorderBlocksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> dict:
    """Reorder blocks atomically."""
    # Verify year exists
    year = db.query(Year).filter(Year.id == year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Year not found",
        )

    # Get all active blocks for this year
    active_blocks = (
        db.query(Block).filter(Block.year_id == year_id, Block.is_active.is_(True)).all()
    )

    active_block_ids = {b.id for b in active_blocks}
    requested_ids = set(request.ordered_block_ids)

    # Verify all requested IDs exist and are active
    if requested_ids != active_block_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ordered_block_ids must contain exactly all active block IDs for this year",
        )

    # Create a mapping of block_id -> order_no
    block_map = {b.id: b for b in active_blocks}

    # Update order_no in a single transaction
    try:
        for order_no, block_id in enumerate(request.ordered_block_ids, start=1):
            block = block_map[block_id]
            block.order_no = order_no

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder blocks: {str(e)}",
        ) from e

    invalidate_syllabus_cache()
    return {"message": "Blocks reordered successfully"}


@router.post(
    "/blocks/{block_id}/themes/reorder",
    summary="Reorder themes",
    description="Atomically reorder themes within a block.",
)
async def reorder_themes(
    block_id: int,
    request: ReorderThemesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> dict:
    """Reorder themes atomically."""
    # Verify block exists
    block = db.query(Block).filter(Block.id == block_id).first()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    # Get all active themes for this block
    active_themes = (
        db.query(Theme).filter(Theme.block_id == block_id, Theme.is_active.is_(True)).all()
    )

    active_theme_ids = {t.id for t in active_themes}
    requested_ids = set(request.ordered_theme_ids)

    # Verify all requested IDs exist and are active
    if requested_ids != active_theme_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ordered_theme_ids must contain exactly all active theme IDs for this block",
        )

    # Create a mapping of theme_id -> order_no
    theme_map = {t.id: t for t in active_themes}

    # Update order_no in a single transaction
    try:
        for order_no, theme_id in enumerate(request.ordered_theme_ids, start=1):
            theme = theme_map[theme_id]
            theme.order_no = order_no

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder themes: {str(e)}",
        ) from e

    invalidate_syllabus_cache()
    return {"message": "Themes reordered successfully"}


# ============================================================================
# CSV Template Download
# ============================================================================


@router.get(
    "/import/templates/years",
    summary="Download years CSV template",
    description="Download CSV template for importing years.",
)
async def download_years_template(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    """Download CSV template for years."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["year_name", "order_no", "is_active"])
    writer.writerow(["1st Year", "1", "true"])

    return {
        "content": output.getvalue(),
        "filename": "years_template.csv",
        "content_type": "text/csv",
    }


@router.get(
    "/import/templates/blocks",
    summary="Download blocks CSV template",
    description="Download CSV template for importing blocks.",
)
async def download_blocks_template(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    """Download CSV template for blocks."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["year_name", "block_code", "block_name", "order_no", "is_active"])
    writer.writerow(["1st Year", "A", "Block A", "1", "true"])

    return {
        "content": output.getvalue(),
        "filename": "blocks_template.csv",
        "content_type": "text/csv",
    }


@router.get(
    "/import/templates/themes",
    summary="Download themes CSV template",
    description="Download CSV template for importing themes.",
)
async def download_themes_template(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    """Download CSV template for themes."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["year_name", "block_code", "theme_title", "order_no", "description", "is_active"]
    )
    writer.writerow(
        [
            "1st Year",
            "A",
            "Cardiovascular System",
            "1",
            "Introduction to cardiovascular anatomy",
            "true",
        ]
    )

    return {
        "content": output.getvalue(),
        "filename": "themes_template.csv",
        "content_type": "text/csv",
    }


# ============================================================================
# CSV Import (Upsert + Dry-run)
# ============================================================================


def _parse_bool(value: str) -> bool:
    """Parse boolean from string (true/false/1/0/yes/no)."""
    value_lower = value.strip().lower()
    return value_lower in ("true", "1", "yes", "on")


def _import_years(
    db: Session,
    content: str,
    dry_run: bool,
    auto_create: bool = False,
) -> CSVImportResult:
    """Import years from CSV."""
    reader = csv.DictReader(io.StringIO(content))
    accepted = 0
    rejected = 0
    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        try:
            year_name = row.get("year_name", "").strip()
            order_no_str = row.get("order_no", "").strip()
            is_active_str = row.get("is_active", "true").strip()

            if not year_name:
                errors.append(
                    {
                        "row": row_num,
                        "reason": "Missing year_name",
                        "data": row,
                    }
                )
                rejected += 1
                continue

            try:
                order_no = int(order_no_str)
                if order_no < 1:
                    raise ValueError("order_no must be >= 1")
            except (ValueError, TypeError):
                errors.append(
                    {
                        "row": row_num,
                        "reason": f"Invalid order_no: {order_no_str}",
                        "data": row,
                    }
                )
                rejected += 1
                continue

            is_active = _parse_bool(is_active_str)

            if dry_run:
                # Just validate
                accepted += 1
            else:
                # Upsert
                existing = db.query(Year).filter(Year.name == year_name).first()
                if existing:
                    existing.order_no = order_no
                    existing.is_active = is_active
                    updated += 1
                else:
                    year = Year(name=year_name, order_no=order_no, is_active=is_active)
                    db.add(year)
                    created += 1
                accepted += 1

        except Exception as e:
            errors.append(
                {
                    "row": row_num,
                    "reason": str(e),
                    "data": row,
                }
            )
            rejected += 1

    if not dry_run:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(
                {
                    "row": 0,
                    "reason": f"Database error: {str(e)}",
                    "data": {},
                }
            )

    return CSVImportResult(
        dry_run=dry_run,
        accepted=accepted,
        rejected=rejected,
        created=created,
        updated=updated,
        errors=errors,
    )


def _import_blocks(
    db: Session,
    content: str,
    dry_run: bool,
    auto_create: bool = False,
) -> CSVImportResult:
    """Import blocks from CSV."""
    reader = csv.DictReader(io.StringIO(content))
    accepted = 0
    rejected = 0
    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            year_name = row.get("year_name", "").strip()
            block_code = row.get("block_code", "").strip()
            block_name = row.get("block_name", "").strip()
            order_no_str = row.get("order_no", "").strip()
            is_active_str = row.get("is_active", "true").strip()

            if not year_name or not block_code or not block_name:
                errors.append(
                    {
                        "row": row_num,
                        "reason": "Missing required field (year_name, block_code, or block_name)",
                        "data": row,
                    }
                )
                rejected += 1
                continue

            # Find year
            year = db.query(Year).filter(Year.name == year_name).first()
            if not year:
                if auto_create:
                    # Create year with default order_no
                    max_order = db.query(Year).count()
                    year = Year(name=year_name, order_no=max_order + 1, is_active=True)
                    db.add(year)
                    db.flush()
                else:
                    errors.append(
                        {
                            "row": row_num,
                            "reason": f"Year '{year_name}' not found",
                            "data": row,
                        }
                    )
                    rejected += 1
                    continue

            try:
                order_no = int(order_no_str)
                if order_no < 1:
                    raise ValueError("order_no must be >= 1")
            except (ValueError, TypeError):
                errors.append(
                    {
                        "row": row_num,
                        "reason": f"Invalid order_no: {order_no_str}",
                        "data": row,
                    }
                )
                rejected += 1
                continue

            is_active = _parse_bool(is_active_str)

            if dry_run:
                accepted += 1
            else:
                # Upsert by year_id + code
                existing = (
                    db.query(Block)
                    .filter(Block.year_id == year.id, Block.code == block_code)
                    .first()
                )
                if existing:
                    existing.name = block_name
                    existing.order_no = order_no
                    existing.is_active = is_active
                    updated += 1
                else:
                    block = Block(
                        year_id=year.id,
                        code=block_code,
                        name=block_name,
                        order_no=order_no,
                        is_active=is_active,
                    )
                    db.add(block)
                    created += 1
                accepted += 1

        except Exception as e:
            errors.append(
                {
                    "row": row_num,
                    "reason": str(e),
                    "data": row,
                }
            )
            rejected += 1

    if not dry_run:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(
                {
                    "row": 0,
                    "reason": f"Database error: {str(e)}",
                    "data": {},
                }
            )

    return CSVImportResult(
        dry_run=dry_run,
        accepted=accepted,
        rejected=rejected,
        created=created,
        updated=updated,
        errors=errors,
    )


def _import_themes(
    db: Session,
    content: str,
    dry_run: bool,
    auto_create: bool = False,
) -> CSVImportResult:
    """Import themes from CSV."""
    reader = csv.DictReader(io.StringIO(content))
    accepted = 0
    rejected = 0
    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            year_name = row.get("year_name", "").strip()
            block_code = row.get("block_code", "").strip()
            theme_title = row.get("theme_title", "").strip()
            order_no_str = row.get("order_no", "").strip()
            description = row.get("description", "").strip() or None
            is_active_str = row.get("is_active", "true").strip()

            if not year_name or not block_code or not theme_title:
                errors.append(
                    {
                        "row": row_num,
                        "reason": "Missing required field (year_name, block_code, or theme_title)",
                        "data": row,
                    }
                )
                rejected += 1
                continue

            # Find year
            year = db.query(Year).filter(Year.name == year_name).first()
            if not year:
                if auto_create:
                    max_order = db.query(Year).count()
                    year = Year(name=year_name, order_no=max_order + 1, is_active=True)
                    db.add(year)
                    db.flush()
                else:
                    errors.append(
                        {
                            "row": row_num,
                            "reason": f"Year '{year_name}' not found",
                            "data": row,
                        }
                    )
                    rejected += 1
                    continue

            # Find block
            block = (
                db.query(Block).filter(Block.year_id == year.id, Block.code == block_code).first()
            )
            if not block:
                if auto_create:
                    # Create block with default order_no
                    max_order = db.query(Block).filter(Block.year_id == year.id).count()
                    block = Block(
                        year_id=year.id,
                        code=block_code,
                        name=f"Block {block_code}",
                        order_no=max_order + 1,
                        is_active=True,
                    )
                    db.add(block)
                    db.flush()
                else:
                    errors.append(
                        {
                            "row": row_num,
                            "reason": f"Block '{block_code}' not found in year '{year_name}'",
                            "data": row,
                        }
                    )
                    rejected += 1
                    continue

            try:
                order_no = int(order_no_str)
                if order_no < 1:
                    raise ValueError("order_no must be >= 1")
            except (ValueError, TypeError):
                errors.append(
                    {
                        "row": row_num,
                        "reason": f"Invalid order_no: {order_no_str}",
                        "data": row,
                    }
                )
                rejected += 1
                continue

            is_active = _parse_bool(is_active_str)
            normalized_title = theme_title.strip()

            if dry_run:
                accepted += 1
            else:
                # Upsert by block_id + title
                existing = (
                    db.query(Theme)
                    .filter(Theme.block_id == block.id, Theme.title.ilike(normalized_title))
                    .first()
                )
                if existing:
                    existing.order_no = order_no
                    existing.description = description
                    existing.is_active = is_active
                    updated += 1
                else:
                    theme = Theme(
                        block_id=block.id,
                        title=normalized_title,
                        order_no=order_no,
                        description=description,
                        is_active=is_active,
                    )
                    db.add(theme)
                    created += 1
                accepted += 1

        except Exception as e:
            errors.append(
                {
                    "row": row_num,
                    "reason": str(e),
                    "data": row,
                }
            )
            rejected += 1

    if not dry_run:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(
                {
                    "row": 0,
                    "reason": f"Database error: {str(e)}",
                    "data": {},
                }
            )

    return CSVImportResult(
        dry_run=dry_run,
        accepted=accepted,
        rejected=rejected,
        created=created,
        updated=updated,
        errors=errors,
    )


@router.post(
    "/import/years",
    response_model=CSVImportResult,
    summary="Import years from CSV",
    description="Import years from CSV file (upsert with dry-run support).",
)
async def import_years(
    file: UploadFile = File(...),
    dry_run: bool = Query(True, description="If true, only validate without writing"),
    auto_create: bool = Query(
        False, description="Auto-create missing parents (not applicable for years)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> CSVImportResult:
    """Import years from CSV."""
    content = (await file.read()).decode("utf-8")
    result = _import_years(db, content, dry_run, auto_create)
    if not dry_run:
        invalidate_syllabus_cache()
    return result


@router.post(
    "/import/blocks",
    response_model=CSVImportResult,
    summary="Import blocks from CSV",
    description="Import blocks from CSV file (upsert with dry-run support).",
)
async def import_blocks(
    file: UploadFile = File(...),
    dry_run: bool = Query(True, description="If true, only validate without writing"),
    auto_create: bool = Query(False, description="Auto-create missing years"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> CSVImportResult:
    """Import blocks from CSV."""
    content = (await file.read()).decode("utf-8")
    result = _import_blocks(db, content, dry_run, auto_create)
    if not dry_run:
        invalidate_syllabus_cache()
    return result


@router.post(
    "/import/themes",
    response_model=CSVImportResult,
    summary="Import themes from CSV",
    description="Import themes from CSV file (upsert with dry-run support).",
)
async def import_themes(
    file: UploadFile = File(...),
    dry_run: bool = Query(True, description="If true, only validate without writing"),
    auto_create: bool = Query(False, description="Auto-create missing years/blocks"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> CSVImportResult:
    """Import themes from CSV."""
    content = (await file.read()).decode("utf-8")
    result = _import_themes(db, content, dry_run, auto_create)
    if not dry_run:
        invalidate_syllabus_cache()
    return result
