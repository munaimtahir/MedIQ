"""Admin import endpoints for bulk question imports."""

import io
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.core.etag import check_if_none_match, compute_etag, create_not_modified_response
from app.db.session import get_db
from app.security.exam_mode_gate import require_not_exam_mode
from app.models.import_schema import (
    ImportFileType,
    ImportJob,
    ImportJobRow,
    ImportJobStatus,
    ImportSchema,
)
from app.models.user import User, UserRole
from app.schemas.import_schema import (
    ActivateSchemaResponse,
    ImportJobListOut,
    ImportJobOut,
    ImportJobResultOut,
    ImportSchemaCreate,
    ImportSchemaListOut,
    ImportSchemaOut,
    ImportSchemaUpdate,
)
from app.services.importer import CSVParser, QuestionValidator, QuestionWriter, RowMapper

router = APIRouter(prefix="/admin/import", tags=["Admin - Import"])

# Max rejected rows to persist (full raw + errors). Beyond that we still count and error_counts.
REJECTED_ROWS_STORAGE_CAP = 2000


# ============================================================================
# Schema Endpoints
# ============================================================================


@router.get("/schemas", response_model=list[ImportSchemaListOut])
async def list_schemas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[ImportSchemaListOut]:
    """List all import schemas."""
    schemas = db.query(ImportSchema).order_by(ImportSchema.name, ImportSchema.version.desc()).all()
    return [ImportSchemaListOut.model_validate(s) for s in schemas]


@router.post("/schemas", response_model=ImportSchemaOut, status_code=status.HTTP_201_CREATED)
async def create_schema(
    schema_data: ImportSchemaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ImportSchemaOut:
    """Create a new import schema (version 1)."""
    # Check if name already exists
    existing = db.query(ImportSchema).filter(ImportSchema.name == schema_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Schema with name '{schema_data.name}' already exists. "
                "Use clone or new-version instead."
            ),
        )

    schema = ImportSchema(
        name=schema_data.name,
        version=1,
        is_active=False,
        file_type=schema_data.file_type,
        delimiter=schema_data.delimiter,
        quote_char=schema_data.quote_char,
        has_header=schema_data.has_header,
        encoding=schema_data.encoding,
        mapping_json=schema_data.mapping_json,
        rules_json=schema_data.rules_json,
        created_by=current_user.id,
    )

    db.add(schema)
    db.commit()
    db.refresh(schema)

    return ImportSchemaOut.model_validate(schema)


@router.post(
    "/schemas/{schema_id}/new-version",
    response_model=ImportSchemaOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_version(
    schema_id: UUID,
    updates: ImportSchemaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ImportSchemaOut:
    """Create a new version of an existing schema (never mutate)."""
    base_schema = db.query(ImportSchema).filter(ImportSchema.id == schema_id).first()
    if not base_schema:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")

    # Get max version for this schema name
    max_version = (
        db.query(ImportSchema.version)
        .filter(ImportSchema.name == base_schema.name)
        .order_by(ImportSchema.version.desc())
        .first()
    )
    new_version = (max_version[0] + 1) if max_version else 1

    # Merge updates with base schema
    new_schema = ImportSchema(
        name=updates.name if updates.name is not None else base_schema.name,
        version=new_version,
        is_active=False,  # New versions start inactive
        file_type=updates.file_type if updates.file_type is not None else base_schema.file_type,
        delimiter=updates.delimiter if updates.delimiter is not None else base_schema.delimiter,
        quote_char=updates.quote_char if updates.quote_char is not None else base_schema.quote_char,
        has_header=updates.has_header if updates.has_header is not None else base_schema.has_header,
        encoding=updates.encoding if updates.encoding is not None else base_schema.encoding,
        mapping_json=(
            updates.mapping_json if updates.mapping_json is not None else base_schema.mapping_json
        ),
        rules_json=updates.rules_json if updates.rules_json is not None else base_schema.rules_json,
        created_by=current_user.id,
    )

    db.add(new_schema)
    db.commit()
    db.refresh(new_schema)

    return ImportSchemaOut.model_validate(new_schema)


@router.post("/schemas/{schema_id}/activate", response_model=ActivateSchemaResponse)
async def activate_schema(
    schema_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ActivateSchemaResponse:
    """Activate a schema (deactivates all others)."""
    schema = db.query(ImportSchema).filter(ImportSchema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")

    # Transaction: deactivate all, then activate one
    db.query(ImportSchema).update({"is_active": False})
    schema.is_active = True

    db.commit()
    db.refresh(schema)

    return ActivateSchemaResponse(
        message=f"Schema '{schema.name}' v{schema.version} activated",
        schema_id=schema.id,
        is_active=True,
    )


@router.get("/schemas/{schema_id}", response_model=ImportSchemaOut)
async def get_schema(
    schema_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ImportSchemaOut:
    """Get a specific schema by ID."""
    schema = db.query(ImportSchema).filter(ImportSchema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")

    return ImportSchemaOut.model_validate(schema)


@router.get("/schemas/{schema_id}/template")
async def download_template(
    schema_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    """Download CSV template for a schema. Supports ETag/If-None-Match for caching."""
    schema = db.query(ImportSchema).filter(ImportSchema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")

    if schema.file_type != ImportFileType.CSV:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template download only supported for CSV schemas",
        )

    # Generate header row from mapping
    headers = []
    for _canonical_field, config in schema.mapping_json.items():
        column_name = config.get("column")
        if column_name:
            headers.append(column_name)

    # Create CSV content
    csv_content = schema.delimiter.join(headers) + "\n"

    # Compute ETag
    etag = compute_etag(csv_content)
    
    # Check If-None-Match
    if check_if_none_match(request, etag):
        return create_not_modified_response(etag)

    filename = f"{schema.name}_v{schema.version}_template.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "ETag": etag,
        },
    )


# ============================================================================
# Import Job Endpoints
# ============================================================================


@router.post(
    "/questions",
    response_model=ImportJobResultOut,
    dependencies=[Depends(require_not_exam_mode("bulk_question_import"))],
)
async def import_questions(
    file: UploadFile = File(...),
    schema_id: Annotated[str | None, Form()] = None,
    dry_run: Annotated[bool, Form()] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ImportJobResultOut:
    """Import questions from CSV (bulk operation, blocked during exam mode)."""
    # Note: dry_run is still allowed even during exam mode (read-only operation)
    # The dependency will block non-dry-run imports
    max_bytes = settings.MAX_BODY_BYTES_IMPORT
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "PAYLOAD_TOO_LARGE",
                "message": "File too large",
                "details": {"limit": max_bytes},
            },
        )

    # Resolve schema
    if schema_id:
        schema = db.query(ImportSchema).filter(ImportSchema.id == UUID(schema_id)).first()
        if not schema:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")
    else:
        # Use active schema
        schema = db.query(ImportSchema).filter(ImportSchema.is_active).first()
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active schema found. Please specify schema_id.",
            )

    file_content = await file.read()

    job = ImportJob(
        schema_id=schema.id,
        schema_name=schema.name,
        schema_version=schema.version,
        created_by=current_user.id,
        filename=file.filename or "unknown.csv",
        file_type=ImportFileType.CSV,
        dry_run=dry_run,
        status=ImportJobStatus.PENDING,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.flush()

    max_rows = settings.IMPORT_MAX_ROWS

    def _truncate_raw(row: dict) -> dict:
        """Truncate raw row values to avoid storing huge payloads."""
        max_val = 400
        out: dict = {}
        for k, v in row.items():
            s = str(v) if v is not None else ""
            if len(s) > max_val:
                s = s[: max_val - 3] + "..."
            out[k] = s
        return out

    try:
        job.status = ImportJobStatus.RUNNING
        parser = CSVParser(schema)
        mapper = RowMapper(schema)
        validator = QuestionValidator(schema, db)
        writer = QuestionWriter(db, current_user.id)

        accepted: list[dict] = []
        rejected_count = 0
        stored_rejected = 0
        error_counts: dict[str, int] = {}

        for row_number, raw_row in parser.parse(file_content):
            if (len(accepted) + rejected_count) >= max_rows:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "VALIDATION_LIMIT_EXCEEDED",
                        "message": "Import row count exceeds maximum allowed",
                        "details": {"limit": max_rows},
                    },
                )

            canonical = mapper.map_row(raw_row)
            errors = validator.validate(canonical)

            if errors:
                rejected_count += 1
                for e in errors:
                    error_counts[e.code] = error_counts.get(e.code, 0) + 1
                if stored_rejected < REJECTED_ROWS_STORAGE_CAP:
                    truncated = _truncate_raw(raw_row)
                    rejected_row = ImportJobRow(
                        job_id=job.id,
                        row_number=row_number,
                        external_id=canonical.get("external_id"),
                        raw_row_json=truncated,
                        errors_json=[e.to_dict() for e in errors],
                    )
                    db.add(rejected_row)
                    stored_rejected += 1
            else:
                accepted.append(canonical)

        if not dry_run and accepted:
            writer.bulk_insert(accepted)

        job.total_rows = len(accepted) + rejected_count
        job.accepted_rows = len(accepted)
        job.rejected_rows = rejected_count
        summary: dict = {
            "error_counts": error_counts,
            "dry_run": dry_run,
        }
        if stored_rejected < rejected_count:
            summary["rejected_csv_max_rows"] = REJECTED_ROWS_STORAGE_CAP
        job.summary_json = summary
        job.status = ImportJobStatus.COMPLETED
        job.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(job)

        return ImportJobResultOut(
            job_id=job.id,
            status=job.status,
            total_rows=job.total_rows,
            accepted_rows=job.accepted_rows,
            rejected_rows=job.rejected_rows,
            summary_json=job.summary_json,
        )

    except HTTPException:
        raise
    except Exception as e:
        job.status = ImportJobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        ) from e


@router.get("/jobs", response_model=list[ImportJobListOut])
async def list_jobs(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[ImportJobListOut]:
    """List import jobs."""
    jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(limit).all()

    return [ImportJobListOut.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=ImportJobOut)
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ImportJobOut:
    """Get job details."""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return ImportJobOut.model_validate(job)


@router.get("/jobs/{job_id}/rejected.csv")
async def download_rejected_csv(
    job_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    """Download rejected rows as CSV. Supports ETag/If-None-Match for caching."""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    rejected_rows = (
        db.query(ImportJobRow)
        .filter(ImportJobRow.job_id == job_id)
        .order_by(ImportJobRow.row_number)
        .all()
    )

    if not rejected_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rejected rows for this job",
        )

    # Build CSV with original columns + error columns
    output = io.StringIO()

    # Get column names from first row
    first_row = rejected_rows[0].raw_row_json
    columns = list(first_row.keys())
    headers = columns + ["row_number", "error_codes", "error_messages"]

    # Write header
    output.write(",".join(headers) + "\n")

    # Write data
    for row in rejected_rows:
        data_row = []
        for col in columns:
            value = str(row.raw_row_json.get(col, ""))
            # Escape quotes
            if "," in value or '"' in value:
                value = '"' + value.replace('"', '""') + '"'
            data_row.append(value)

        # Add error info
        error_codes = "; ".join(e["code"] for e in row.errors_json)
        error_messages = "; ".join(e["message"] for e in row.errors_json)

        data_row.append(str(row.row_number))
        data_row.append(f'"{error_codes}"')
        data_row.append(f'"{error_messages}"')

        output.write(",".join(data_row) + "\n")

    csv_content = output.getvalue()

    # Compute ETag based on content
    csv_content_str = output.getvalue()
    etag = compute_etag(csv_content_str)
    
    # Check If-None-Match
    if check_if_none_match(request, etag):
        return create_not_modified_response(etag)
    
    return Response(
        content=csv_content_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="job_{job_id}_rejected.csv"',
            "ETag": etag,
        },
    )
