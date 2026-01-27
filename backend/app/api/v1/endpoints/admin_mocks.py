"""Admin mock blueprint and generation endpoints."""

import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.pagination import PaginatedResponse, PaginationParams, pagination_params
from app.core.audit import write_audit
from app.core.dependencies import get_current_user, get_db
from app.mocks.contracts import MockBlueprintConfig
from app.mocks.generator import generate_mock_questions
from app.models.mock import (
    MockBlueprint,
    MockBlueprintMode,
    MockBlueprintStatus,
    MockBlueprintVersion,
    MockGenerationRun,
    MockGenerationRunStatus,
    MockInstance,
)
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/mocks", tags=["Admin - Mock Blueprints"])


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")


def require_admin_or_reviewer(user: User) -> None:
    """Require user to be ADMIN or REVIEWER."""
    if user.role not in (UserRole.ADMIN, UserRole.REVIEWER):
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")


# Police mode confirmation phrases
MOCK_PHRASES = {
    "activate": "ACTIVATE MOCK BLUEPRINT",
    "archive": "ARCHIVE MOCK BLUEPRINT",
    "generate": "GENERATE MOCK",
}


# ============================================================================
# Request/Response Models
# ============================================================================


class MockBlueprintCreate(BaseModel):
    """Request to create a mock blueprint."""

    title: str = Field(..., min_length=1, max_length=500)
    year: int = Field(..., ge=1)
    total_questions: int = Field(..., ge=1, le=300)
    duration_minutes: int = Field(..., ge=1)
    mode: str = Field(default="EXAM", description="EXAM or TUTOR")
    config: dict[str, Any] = Field(..., description="Blueprint configuration")


class MockBlueprintUpdate(BaseModel):
    """Request to update a mock blueprint."""

    title: str | None = Field(None, min_length=1, max_length=500)
    total_questions: int | None = Field(None, ge=1, le=300)
    duration_minutes: int | None = Field(None, ge=1)
    config: dict[str, Any] | None = None


class MockBlueprintOut(BaseModel):
    """Mock blueprint response."""

    id: UUID
    title: str
    year: int
    total_questions: int
    duration_minutes: int
    mode: str
    status: str
    config: dict[str, Any]
    created_by: UUID
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MockBlueprintVersionOut(BaseModel):
    """Mock blueprint version response."""

    id: UUID
    blueprint_id: UUID
    version: int
    config: dict[str, Any]
    created_by: UUID
    created_at: str
    diff_summary: str | None

    class Config:
        from_attributes = True


class MockBlueprintActivateRequest(BaseModel):
    """Request to activate a mock blueprint."""

    reason: str = Field(..., min_length=10, description="Reason for activation (min 10 chars)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase")


class MockBlueprintArchiveRequest(BaseModel):
    """Request to archive a mock blueprint."""

    reason: str = Field(..., min_length=10, description="Reason for archiving (min 10 chars)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase")


class MockGenerateRequest(BaseModel):
    """Request to generate a mock instance."""

    seed: int | None = Field(None, description="Seed for deterministic generation (auto-generated if null)")
    reason: str = Field(..., min_length=10, description="Reason for generation (min 10 chars)")
    confirmation_phrase: str = Field(..., description="Confirmation phrase")


class MockGenerateResponse(BaseModel):
    """Response from mock generation."""

    run_id: UUID
    mock_instance_id: UUID
    seed: int
    warnings: list[dict[str, Any]]
    generated_question_count: int


class MockGenerationRunOut(BaseModel):
    """Mock generation run response."""

    id: UUID
    blueprint_id: UUID
    status: str
    seed: int
    config_version_id: UUID | None
    requested_by: UUID
    started_at: str | None
    finished_at: str | None
    generated_question_count: int
    warnings: list[dict[str, Any]] | None
    errors: list[dict[str, Any]] | None
    created_at: str

    class Config:
        from_attributes = True


class MockInstanceOut(BaseModel):
    """Mock instance response."""

    id: UUID
    blueprint_id: UUID
    generation_run_id: UUID
    year: int
    total_questions: int
    duration_minutes: int
    seed: int
    question_ids: list[str]
    meta: dict[str, Any] | None
    created_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Blueprint CRUD
# ============================================================================


@router.post("/blueprints", response_model=MockBlueprintOut, status_code=status.HTTP_201_CREATED)
async def create_blueprint(
    request: MockBlueprintCreate,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Create a new mock blueprint."""
    require_admin_or_reviewer(current_user)

    # Validate config
    try:
        config_obj = MockBlueprintConfig.model_validate(request.config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid config: {str(e)}") from e

    # Validate config against total_questions
    warnings = config_obj.validate_against_total_questions(request.total_questions)
    if warnings:
        logger.warning(f"Blueprint config warnings: {warnings}")

    # Validate mode
    try:
        mode = MockBlueprintMode(request.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")

    # Create blueprint
    blueprint = MockBlueprint(
        title=request.title,
        year=request.year,
        total_questions=request.total_questions,
        duration_minutes=request.duration_minutes,
        mode=mode,
        status=MockBlueprintStatus.DRAFT,
        config=request.config,
        created_by=current_user.id,
    )
    db.add(blueprint)
    db.flush()

    # Create initial version
    version = MockBlueprintVersion(
        blueprint_id=blueprint.id,
        version=1,
        config=request.config,
        created_by=current_user.id,
        diff_summary="Initial version",
    )
    db.add(version)
    db.commit()
    db.refresh(blueprint)

    # Audit log
    write_audit(
        db,
        current_user.id,
        "MOCK_BLUEPRINT_CREATE",
        "MOCK_BLUEPRINT",
        blueprint.id,
        after={"title": blueprint.title, "year": blueprint.year, "status": blueprint.status.value},
    )
    db.commit()

    return MockBlueprintOut.model_validate(blueprint)


@router.get("/blueprints", response_model=PaginatedResponse[MockBlueprintOut])
async def list_blueprints(
    year: Annotated[int | None, Query(description="Filter by year")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """List mock blueprints."""
    require_admin_or_reviewer(current_user)

    query = db.query(MockBlueprint)

    if year:
        query = query.filter(MockBlueprint.year == year)
    if status_filter:
        try:
            status_enum = MockBlueprintStatus(status_filter.upper())
            query = query.filter(MockBlueprint.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    query = query.order_by(MockBlueprint.updated_at.desc())
    total = query.count()
    blueprints = query.offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedResponse(
        items=[MockBlueprintOut.model_validate(bp) for bp in blueprints],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/blueprints/{blueprint_id}", response_model=MockBlueprintOut)
async def get_blueprint(
    blueprint_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Get a mock blueprint by ID."""
    require_admin_or_reviewer(current_user)

    blueprint = db.query(MockBlueprint).filter(MockBlueprint.id == blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    return MockBlueprintOut.model_validate(blueprint)


@router.put("/blueprints/{blueprint_id}", response_model=MockBlueprintOut)
async def update_blueprint(
    blueprint_id: UUID,
    request: MockBlueprintUpdate,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Update a mock blueprint (creates new version)."""
    require_admin_or_reviewer(current_user)

    blueprint = db.query(MockBlueprint).filter(MockBlueprint.id == blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    if blueprint.status == MockBlueprintStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Cannot update archived blueprint")

    # Get current version
    current_version = (
        db.query(MockBlueprintVersion)
        .filter(MockBlueprintVersion.blueprint_id == blueprint_id)
        .order_by(MockBlueprintVersion.version.desc())
        .first()
    )
    if not current_version:
        raise HTTPException(status_code=500, detail="No version found for blueprint")

    # Prepare updates
    before_state = {
        "title": blueprint.title,
        "total_questions": blueprint.total_questions,
        "duration_minutes": blueprint.duration_minutes,
        "config": blueprint.config,
    }

    if request.title is not None:
        blueprint.title = request.title
    if request.total_questions is not None:
        blueprint.total_questions = request.total_questions
    if request.duration_minutes is not None:
        blueprint.duration_minutes = request.duration_minutes

    # Update config if provided
    new_config = request.config if request.config is not None else blueprint.config
    if request.config is not None:
        # Validate new config
        try:
            config_obj = MockBlueprintConfig.model_validate(new_config)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid config: {str(e)}") from e

        # Validate against total_questions
        total_q = blueprint.total_questions
        warnings = config_obj.validate_against_total_questions(total_q)
        if warnings:
            logger.warning(f"Blueprint config warnings: {warnings}")

        blueprint.config = new_config

    blueprint.updated_at = datetime.now(timezone.utc)
    db.flush()

    # Create new version
    new_version_num = current_version.version + 1
    version = MockBlueprintVersion(
        blueprint_id=blueprint.id,
        version=new_version_num,
        config=blueprint.config,
        created_by=current_user.id,
        diff_summary=f"Updated by {current_user.email}",
    )
    db.add(version)
    db.commit()
    db.refresh(blueprint)

    # Audit log
    after_state = {
        "title": blueprint.title,
        "total_questions": blueprint.total_questions,
        "duration_minutes": blueprint.duration_minutes,
        "config": blueprint.config,
    }
    write_audit(
        db,
        current_user.id,
        "MOCK_BLUEPRINT_UPDATE",
        "MOCK_BLUEPRINT",
        blueprint.id,
        before=before_state,
        after=after_state,
    )
    db.commit()

    return MockBlueprintOut.model_validate(blueprint)


@router.post("/blueprints/{blueprint_id}/activate", response_model=MockBlueprintOut)
async def activate_blueprint(
    blueprint_id: UUID,
    request: MockBlueprintActivateRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Activate a mock blueprint (requires police mode confirmation)."""
    require_admin(current_user)

    # Validate confirmation phrase
    phrase_upper = request.confirmation_phrase.strip().upper()
    if phrase_upper != MOCK_PHRASES["activate"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: {MOCK_PHRASES['activate']}",
        )

    blueprint = db.query(MockBlueprint).filter(MockBlueprint.id == blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    if blueprint.status == MockBlueprintStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Cannot activate archived blueprint")

    before_status = blueprint.status.value
    blueprint.status = MockBlueprintStatus.ACTIVE
    blueprint.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(blueprint)

    # Audit log
    write_audit(
        db,
        current_user.id,
        "MOCK_BLUEPRINT_ACTIVATE",
        "MOCK_BLUEPRINT",
        blueprint.id,
        before={"status": before_status},
        after={"status": blueprint.status.value},
        meta={"reason": request.reason, "confirmation_phrase": request.confirmation_phrase},
    )
    db.commit()

    return MockBlueprintOut.model_validate(blueprint)


@router.post("/blueprints/{blueprint_id}/archive", response_model=MockBlueprintOut)
async def archive_blueprint(
    blueprint_id: UUID,
    request: MockBlueprintArchiveRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Archive a mock blueprint (requires police mode confirmation)."""
    require_admin(current_user)

    # Validate confirmation phrase
    phrase_upper = request.confirmation_phrase.strip().upper()
    if phrase_upper != MOCK_PHRASES["archive"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: {MOCK_PHRASES['archive']}",
        )

    blueprint = db.query(MockBlueprint).filter(MockBlueprint.id == blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    before_status = blueprint.status.value
    blueprint.status = MockBlueprintStatus.ARCHIVED
    blueprint.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(blueprint)

    # Audit log
    write_audit(
        db,
        current_user.id,
        "MOCK_BLUEPRINT_ARCHIVE",
        "MOCK_BLUEPRINT",
        blueprint.id,
        before={"status": before_status},
        after={"status": blueprint.status.value},
        meta={"reason": request.reason, "confirmation_phrase": request.confirmation_phrase},
    )
    db.commit()

    return MockBlueprintOut.model_validate(blueprint)


# ============================================================================
# Generation
# ============================================================================


@router.post("/blueprints/{blueprint_id}/generate", response_model=MockGenerateResponse)
async def generate_mock(
    blueprint_id: UUID,
    request: MockGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Generate a mock instance (requires police mode confirmation)."""
    require_admin(current_user)

    # Validate confirmation phrase
    phrase_upper = request.confirmation_phrase.strip().upper()
    if phrase_upper != MOCK_PHRASES["generate"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: {MOCK_PHRASES['generate']}",
        )

    blueprint = db.query(MockBlueprint).filter(MockBlueprint.id == blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    if blueprint.status != MockBlueprintStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Blueprint must be ACTIVE to generate mocks")

    # Get latest config version
    config_version = (
        db.query(MockBlueprintVersion)
        .filter(MockBlueprintVersion.blueprint_id == blueprint_id)
        .order_by(MockBlueprintVersion.version.desc())
        .first()
    )
    if not config_version:
        raise HTTPException(status_code=500, detail="No config version found for blueprint")

    # Generate seed if not provided
    seed = request.seed if request.seed is not None else secrets.randbelow(2**31)

    # Create generation run
    run = MockGenerationRun(
        blueprint_id=blueprint.id,
        status=MockGenerationRunStatus.RUNNING.value,
        seed=seed,
        config_version_id=config_version.id,
        requested_by=current_user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    try:
        # Validate config
        config_obj = MockBlueprintConfig.model_validate(blueprint.config)

        # Generate questions
        now = datetime.now(timezone.utc)
        question_ids, meta, warnings = generate_mock_questions(
            db, blueprint, config_obj, seed, now
        )

        # Create mock instance
        instance = MockInstance(
            blueprint_id=blueprint.id,
            generation_run_id=run.id,
            year=blueprint.year,
            total_questions=len(question_ids),
            duration_minutes=blueprint.duration_minutes,
            seed=seed,
            question_ids=question_ids,
            meta=meta,
        )
        db.add(instance)
        db.flush()

        # Update run
        run.status = MockGenerationRunStatus.DONE.value
        run.finished_at = datetime.now(timezone.utc)
        run.generated_question_count = len(question_ids)
        run.warnings = warnings if warnings else None
        db.commit()

        # Audit log
        write_audit(
            db,
            current_user.id,
            "MOCK_GENERATE_RUN",
            "MOCK_GENERATION_RUN",
            run.id,
            after={
                "blueprint_id": str(blueprint.id),
                "status": run.status.value,
                "seed": seed,
                "question_count": len(question_ids),
            },
            meta={"reason": request.reason, "confirmation_phrase": request.confirmation_phrase},
        )
        db.commit()

        return MockGenerateResponse(
            run_id=run.id,
            mock_instance_id=instance.id,
            seed=seed,
            warnings=warnings,
            generated_question_count=len(question_ids),
        )

    except Exception as e:
        # Mark run as failed
        run.status = MockGenerationRunStatus.FAILED.value
        run.finished_at = datetime.now(timezone.utc)
        run.errors = [{"type": "generation_error", "message": str(e)}]
        db.commit()

        logger.exception(f"Mock generation failed for blueprint {blueprint_id}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}") from e


# ============================================================================
# Runs and Instances
# ============================================================================


@router.get("/runs", response_model=PaginatedResponse[MockGenerationRunOut])
async def list_runs(
    blueprint_id: Annotated[UUID | None, Query(description="Filter by blueprint ID")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """List mock generation runs."""
    require_admin_or_reviewer(current_user)

    query = db.query(MockGenerationRun)

    if blueprint_id:
        query = query.filter(MockGenerationRun.blueprint_id == blueprint_id)

    query = query.order_by(MockGenerationRun.created_at.desc())
    total = query.count()
    runs = query.offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedResponse(
        items=[MockGenerationRunOut.model_validate(run) for run in runs],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/runs/{run_id}", response_model=MockGenerationRunOut)
async def get_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Get a mock generation run by ID."""
    require_admin_or_reviewer(current_user)

    run = db.query(MockGenerationRun).filter(MockGenerationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return MockGenerationRunOut.model_validate(run)


@router.get("/instances", response_model=PaginatedResponse[MockInstanceOut])
async def list_instances(
    blueprint_id: Annotated[UUID | None, Query(description="Filter by blueprint ID")] = None,
    pagination: Annotated[PaginationParams, Depends(pagination_params)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """List mock instances."""
    require_admin_or_reviewer(current_user)

    query = db.query(MockInstance)

    if blueprint_id:
        query = query.filter(MockInstance.blueprint_id == blueprint_id)

    query = query.order_by(MockInstance.created_at.desc())
    total = query.count()
    instances = query.offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedResponse(
        items=[MockInstanceOut.model_validate(inst) for inst in instances],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/instances/{instance_id}", response_model=MockInstanceOut)
async def get_instance(
    instance_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """Get a mock instance by ID."""
    require_admin_or_reviewer(current_user)

    instance = db.query(MockInstance).filter(MockInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    return MockInstanceOut.model_validate(instance)
