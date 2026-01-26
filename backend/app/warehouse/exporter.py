"""Warehouse export pipeline (file-based, shadow mode only).

Exports Postgres data to local JSONL files with manifests.
Snowflake loading is deferred (active mode treated as shadow for now).
"""

import hashlib
import json
import logging
from collections.abc import Iterator
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.warehouse import (
    WarehouseExportDataset,
    WarehouseExportRun,
    WarehouseExportRunStatus,
    WarehouseExportRunType,
    WarehouseExportState,
)
from app.warehouse.contracts import (
    AttemptExportRow,
    EventExportRow,
    ExportEnvelope,
    MasterySnapshotExportRow,
    RevisionQueueDailyExportRow,
)
from app.warehouse.mappers import (
    map_attempts,
    map_events,
    map_mastery_snapshots,
    map_revision_queue_daily,
)

logger = logging.getLogger(__name__)

# Export configuration
EXPORT_BASE_DIR = Path("backend/warehouse/exports")
ROWS_PER_FILE = 50_000  # Chunk size for part files


def _get_warehouse_mode(db: Session) -> tuple[str, bool]:
    """
    Get warehouse mode and freeze status from runtime config.

    Returns:
        (warehouse_mode, warehouse_freeze)
    """
    config = db.query(AlgoRuntimeConfig).order_by(AlgoRuntimeConfig.updated_at.desc()).first()
    if not config:
        return "disabled", False

    config_json = config.config_json or {}
    warehouse_mode = config_json.get("warehouse_mode", "disabled")
    warehouse_freeze = config_json.get("warehouse_freeze", False)

    return warehouse_mode, warehouse_freeze


def get_effective_warehouse_mode(db: Session) -> tuple[str, list[str]]:
    """
    Compute effective warehouse mode based on requested mode and readiness.

    Rules:
    1) If requested_mode == "disabled" => effective_mode="disabled"
    2) If requested_mode == "shadow" => effective_mode="shadow" (no Snowflake connect/load)
    3) If requested_mode == "active":
       - If freeze==true => effective_mode="shadow" + warning "frozen_fallback_shadow"
       - Else evaluate readiness:
         - if ready => effective_mode="active"
         - else => effective_mode="shadow" + warning "not_ready_fallback_shadow"

    Returns:
        (effective_mode, warnings)
    """
    from app.warehouse.readiness import evaluate_warehouse_readiness

    requested_mode, warehouse_freeze = _get_warehouse_mode(db)
    warnings: list[str] = []

    if requested_mode == "disabled":
        return "disabled", warnings

    if requested_mode == "shadow":
        return "shadow", warnings

    if requested_mode == "active":
        if warehouse_freeze:
            warnings.append("frozen_fallback_shadow")
            return "shadow", warnings

        # Evaluate readiness
        readiness = evaluate_warehouse_readiness(db)
        if readiness.ready:
            return "active", warnings
        else:
            warnings.append("not_ready_fallback_shadow")
            return "shadow", warnings

    # Fallback for invalid mode
    return "disabled", warnings


def _get_watermark(db: Session, dataset: str) -> datetime | date | None:
    """Get watermark for a dataset from warehouse_export_state."""
    state = db.query(WarehouseExportState).filter(WarehouseExportState.id == 1).first()
    if not state:
        return None

    if dataset == "attempts":
        return state.attempts_watermark
    elif dataset == "events":
        return state.events_watermark
    elif dataset == "mastery":
        return state.mastery_watermark
    elif dataset == "revision_queue":
        return state.revision_queue_watermark

    return None


def _update_watermark(db: Session, dataset: str, watermark: datetime | date) -> None:
    """Update watermark for a dataset in warehouse_export_state."""
    state = db.query(WarehouseExportState).filter(WarehouseExportState.id == 1).first()
    if not state:
        # Create singleton if missing
        state = WarehouseExportState(id=1)
        db.add(state)
        db.flush()

    if dataset == "attempts":
        state.attempts_watermark = watermark
    elif dataset == "events":
        state.events_watermark = watermark
    elif dataset == "mastery":
        state.mastery_watermark = watermark
    elif dataset == "revision_queue":
        state.revision_queue_watermark = watermark

    state.updated_at = datetime.now(timezone.utc)
    db.commit()


def _compute_file_checksum(file_path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _write_jsonl_file(file_path: Path, rows: Iterator[dict[str, Any]]) -> int:
    """
    Write rows to a JSONL file.

    Returns:
        Number of rows written
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(file_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")
            count += 1
    return count


def _write_manifest(
    run_id: UUID,
    dataset: str,
    range_start: datetime | date | None,
    range_end: datetime | date | None,
    rows_exported: int,
    file_paths: list[Path],
    export_dir: Path,
) -> Path:
    """Write manifest file for an export run."""
    checksums = {}
    for file_path in file_paths:
        if file_path.exists():
            checksums[file_path.name] = _compute_file_checksum(file_path)

    manifest = {
        "run_id": str(run_id),
        "dataset": dataset,
        "range_start": range_start.isoformat() if range_start else None,
        "range_end": range_end.isoformat() if range_end else None,
        "rows": rows_exported,
        "files": [str(p.relative_to(export_dir)) for p in file_paths],
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checksums": checksums,
    }

    manifest_dir = export_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{run_id}.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    return manifest_path


def _export_dataset_to_files(
    db: Session,
    run_id: UUID,
    dataset: str,
    range_start: datetime | date | None,
    range_end: datetime | date | None,
    export_dir: Path,
) -> tuple[int, list[Path]]:
    """
    Export a dataset to JSONL files.

    Returns:
        (rows_exported, file_paths)
    """
    # Get mapper function and determine date_part for directory structure
    if dataset == "attempts":
        mapper = map_attempts(db, range_start, range_end)
        date_part = (
            range_end.date()
            if isinstance(range_end, datetime)
            else (range_end if isinstance(range_end, date) else datetime.now(timezone.utc).date())
        )
    elif dataset == "events":
        mapper = map_events(db, range_start, range_end)
        date_part = (
            range_end.date()
            if isinstance(range_end, datetime)
            else (range_end if isinstance(range_end, date) else datetime.now(timezone.utc).date())
        )
    elif dataset == "mastery":
        mapper = map_mastery_snapshots(db, range_start, range_end)
        date_part = (
            range_end.date()
            if isinstance(range_end, datetime)
            else (range_end if isinstance(range_end, date) else datetime.now(timezone.utc).date())
        )
    elif dataset == "revision_queue":
        if not isinstance(range_start, date) or not isinstance(range_end, date):
            raise ValueError("revision_queue requires date range")
        mapper = map_revision_queue_daily(db, range_start, range_end)
        date_part = range_end
    else:
        raise ValueError(f"Unknown dataset: {dataset}")

    # Build export path structure: dataset/YYYY/MM/DD/run_id/
    year = date_part.year
    month = date_part.month
    day = date_part.day
    dataset_dir = export_dir / dataset / str(year) / f"{month:02d}" / f"{day:02d}" / str(run_id)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    # Stream rows and write to part files
    file_paths: list[Path] = []
    total_rows = 0
    part_num = 0
    current_batch: list[dict[str, Any]] = []

    for row in mapper:
        # Convert Pydantic model to dict
        row_dict = row.model_dump() if hasattr(row, "model_dump") else row.dict()
        current_batch.append(row_dict)
        total_rows += 1

        # Write part file when batch is full
        if len(current_batch) >= ROWS_PER_FILE:
            part_num += 1
            part_file = dataset_dir / f"part-{part_num:04d}.jsonl"
            _write_jsonl_file(part_file, iter(current_batch))
            file_paths.append(part_file)
            current_batch = []

    # Write final part file if there are remaining rows
    if current_batch:
        part_num += 1
        part_file = dataset_dir / f"part-{part_num:04d}.jsonl"
        _write_jsonl_file(part_file, iter(current_batch))
        file_paths.append(part_file)

    return total_rows, file_paths


def start_export(
    db: Session,
    dataset: str,
    run_type: str,
    range_start: datetime | date | None,
    range_end: datetime | date | None,
    actor_user_id: UUID | None,
    reason: str | None,
) -> UUID:
    """
    Start an export run (creates run record, checks guards, may block).

    Returns:
        run_id (UUID)
    """
    run_id = uuid4()

    # Check runtime mode and freeze
    warehouse_mode, warehouse_freeze = _get_warehouse_mode(db)

    # Create run record
    run = WarehouseExportRun(
        run_id=run_id,
        run_type=WarehouseExportRunType(run_type),
        dataset=WarehouseExportDataset(dataset),
        range_start=range_start,
        range_end=range_end,
        status=WarehouseExportRunStatus.QUEUED,
        details={
            "reason": reason,
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
        },
    )
    db.add(run)
    db.flush()

    # Check guards
    if warehouse_mode == "disabled":
        run.status = WarehouseExportRunStatus.BLOCKED_DISABLED
        run.last_error = "Warehouse mode is disabled"
        db.commit()
        logger.warning(f"Export run {run_id} blocked: warehouse mode disabled")
        return run_id

    if warehouse_freeze:
        run.status = WarehouseExportRunStatus.BLOCKED_FROZEN
        run.last_error = "Warehouse updates are frozen"
        db.commit()
        logger.warning(f"Export run {run_id} blocked: warehouse frozen")
        return run_id

    # Run export
    try:
        run.status = WarehouseExportRunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        # Export to files (use absolute path)
        export_dir = Path(EXPORT_BASE_DIR).resolve()
        rows_exported, file_paths = _export_dataset_to_files(
            db, run_id, dataset, range_start, range_end, export_dir
        )

        # Write manifest
        manifest_path = _write_manifest(
            run_id, dataset, range_start, range_end, rows_exported, file_paths, export_dir
        )

        # Update run record
        run.rows_exported = rows_exported
        run.files_written = len(file_paths)
        run.manifest_path = str(manifest_path.relative_to(export_dir))
        run.finished_at = datetime.now(timezone.utc)

        # Set status based on mode
        if warehouse_mode == "shadow":
            run.status = WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY
        elif warehouse_mode == "active":
            run.status = WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY  # Same as shadow for now
            run.details = run.details or {}
            run.details["warning"] = "active_mode_no_snowflake_loader_yet"

        # Update watermark on success
        if range_end:
            if dataset == "revision_queue" and isinstance(range_end, date):
                _update_watermark(db, dataset, range_end)
            elif isinstance(range_end, datetime):
                _update_watermark(db, dataset, range_end)

        db.commit()
        logger.info(
            f"Export run {run_id} completed: {rows_exported} rows, {len(file_paths)} files"
        )

    except Exception as e:
        logger.error(f"Export run {run_id} failed: {e}", exc_info=True)
        run.status = WarehouseExportRunStatus.FAILED
        run.last_error = str(e)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        # Watermark is NOT updated on failure

    return run_id


def compute_next_ranges_from_watermarks(db: Session) -> dict[str, tuple[datetime | date | None, datetime | date | None]]:
    """
    Compute next export ranges from watermarks.

    Returns:
        {dataset: (range_start, range_end)}
    """
    now = datetime.now(timezone.utc)
    today = date.today()

    ranges = {}

    # Attempts
    attempts_watermark = _get_watermark(db, "attempts")
    ranges["attempts"] = (attempts_watermark, now)

    # Events
    events_watermark = _get_watermark(db, "events")
    ranges["events"] = (events_watermark, now)

    # Mastery
    mastery_watermark = _get_watermark(db, "mastery")
    ranges["mastery"] = (mastery_watermark, now)

    # Revision queue (date-based)
    revision_watermark = _get_watermark(db, "revision_queue")
    ranges["revision_queue"] = (revision_watermark, today)

    return ranges


def run_incremental_exports(db: Session, actor_user_id: UUID | None, reason: str | None) -> list[UUID]:
    """
    Run incremental exports for all datasets (attempts, events, mastery).

    Orchestrates exports from watermarks to now.
    """
    ranges = compute_next_ranges_from_watermarks(db)
    run_ids = []

    for dataset in ["attempts", "events", "mastery"]:
        range_start, range_end = ranges[dataset]
        if range_start is None:
            # First run - export all data up to now
            logger.info(f"First incremental export for {dataset}: exporting all data")
        else:
            logger.info(f"Incremental export for {dataset}: {range_start} to {range_end}")

        run_id = start_export(
            db, dataset, "incremental", range_start, range_end, actor_user_id, reason
        )
        run_ids.append(run_id)

    return run_ids


def run_backfill(
    db: Session,
    dataset: str,
    range_start: datetime | date,
    range_end: datetime | date,
    actor_user_id: UUID | None,
    reason: str | None,
) -> UUID:
    """
    Run a backfill export for a specific dataset and time range.
    """
    return start_export(db, dataset, "backfill", range_start, range_end, actor_user_id, reason)
