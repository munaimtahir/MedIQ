"""Model registry for Mistake Engine v1."""

import json
import logging
import pickle
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.mistakes_v1.schemas import CalibrationType, ModelStatus, ModelType
from app.models.mistakes import MistakeModelVersion

logger = logging.getLogger(__name__)

# Storage path for model artifacts
STORAGE_BASE = Path("backend/storage/models/mistakes_v1")


def get_model_storage_path(model_version_id: UUID) -> Path:
    """
    Get storage path for a model version.

    Args:
        model_version_id: Model version ID

    Returns:
        Path to model directory
    """
    return STORAGE_BASE / str(model_version_id)


def save_model_artifact(
    model_version_id: UUID,
    model: Any,
    metadata: dict[str, Any] | None = None,
) -> str:
    """
    Save model artifact to disk.

    Args:
        model_version_id: Model version ID
        model: Trained model object (pickle-able)
        metadata: Optional metadata to save alongside model

    Returns:
        Path to saved artifact
    """
    storage_path = get_model_storage_path(model_version_id)
    storage_path.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = storage_path / "model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Save metadata if provided
    if metadata:
        metadata_path = storage_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    logger.info(f"Saved model artifact to {model_path}")
    return str(model_path)


def load_model_artifact(model_version_id: UUID) -> tuple[Any, dict[str, Any] | None]:
    """
    Load model artifact from disk.

    Args:
        model_version_id: Model version ID

    Returns:
        Tuple of (model, metadata) or (None, None) if not found
    """
    storage_path = get_model_storage_path(model_version_id)
    model_path = storage_path / "model.pkl"

    if not model_path.exists():
        logger.warning(f"Model artifact not found: {model_path}")
        return None, None

    # Load model
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Load metadata if available
    metadata_path = storage_path / "metadata.json"
    metadata = None
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

    return model, metadata


async def get_active_model_version(db: AsyncSession) -> MistakeModelVersion | None:
    """
    Get the active model version.

    Args:
        db: Database session

    Returns:
        Active MistakeModelVersion or None
    """
    stmt = select(MistakeModelVersion).where(MistakeModelVersion.status == ModelStatus.ACTIVE)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_model_version_by_id(
    db: AsyncSession,
    model_version_id: UUID,
) -> MistakeModelVersion | None:
    """
    Get model version by ID.

    Args:
        db: Database session
        model_version_id: Model version ID

    Returns:
        MistakeModelVersion or None
    """
    return await db.get(MistakeModelVersion, model_version_id)


async def activate_model_version(
    db: AsyncSession,
    model_version_id: UUID,
) -> MistakeModelVersion | None:
    """
    Activate a model version (deactivates all others).

    Args:
        db: Database session
        model_version_id: Model version ID to activate

    Returns:
        Activated MistakeModelVersion or None if not found
    """
    # Get target version
    model_version = await db.get(MistakeModelVersion, model_version_id)
    if not model_version:
        logger.warning(f"Model version not found: {model_version_id}")
        return None

    # Deactivate all other versions
    stmt = select(MistakeModelVersion).where(
        MistakeModelVersion.status == ModelStatus.ACTIVE,
        MistakeModelVersion.id != model_version_id,
    )
    result = await db.execute(stmt)
    other_versions = result.scalars().all()

    for other in other_versions:
        other.status = ModelStatus.DEPRECATED

    # Activate target
    model_version.status = ModelStatus.ACTIVE
    await db.commit()
    await db.refresh(model_version)

    logger.info(f"Activated model version {model_version_id}")
    return model_version


async def create_model_version(
    db: AsyncSession,
    model_type: ModelType,
    feature_schema_version: str,
    label_schema_version: str,
    training_window_start: date | None = None,
    training_window_end: date | None = None,
    metrics_json: dict[str, Any] | None = None,
    artifact_path: str | None = None,
    calibration_type: CalibrationType | None = None,
    notes: str | None = None,
) -> MistakeModelVersion:
    """
    Create a new model version (in DRAFT status).

    Args:
        db: Database session
        model_type: Model type
        feature_schema_version: Feature schema version
        label_schema_version: Label schema version
        training_window_start: Training window start date
        training_window_end: Training window end date
        metrics_json: Training metrics
        artifact_path: Path to model artifact
        calibration_type: Calibration method
        notes: Optional notes

    Returns:
        Created MistakeModelVersion
    """
    model_version = MistakeModelVersion(
        status=ModelStatus.DRAFT,
        model_type=model_type.value,
        feature_schema_version=feature_schema_version,
        label_schema_version=label_schema_version,
        training_window_start=training_window_start,
        training_window_end=training_window_end,
        metrics_json=metrics_json or {},
        artifact_path=artifact_path,
        calibration_type=calibration_type.value if calibration_type else None,
        notes=notes,
    )

    db.add(model_version)
    await db.commit()
    await db.refresh(model_version)

    logger.info(f"Created model version {model_version.id} (DRAFT)")
    return model_version
