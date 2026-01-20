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

from app.core.dependencies import require_roles
from app.db.session import get_db
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

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


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
            detail=f"Schema with name '{schema_data.name}' already exists. Use clone or new-version instead.",
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    """Download CSV template for a schema."""
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
    for canonical_field, config in schema.mapping_json.items():
        column_name = config.get("column")
        if column_name:
            headers.append(column_name)

    # Create CSV content
    csv_content = schema.delimiter.join(headers) + "\n"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{schema.name}_v{schema.version}_template.csv"'
        },
    )


# ============================================================================
# Import Job Endpoints
# ============================================================================


@router.post("/questions", response_model=ImportJobResultOut)
async def import_questions(
    file: UploadFile = File(...),
    schema_id: Annotated[str | None, Form()] = None,
    dry_run: Annotated[bool, Form()] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ImportJobResultOut:
    """Import questions from CSV file."""
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # Resolve schema
    if schema_id:
        schema = db.query(ImportSchema).filter(ImportSchema.id == UUID(schema_id)).first()
        if not schema:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")
    else:
        # Use active schema
        schema = db.query(ImportSchema).filter(ImportSchema.is_active == True).first()
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active schema found. Please specify schema_id.",
            )

    # Read file content
    file_content = await file.read()

    # Create import job
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

    try:
        # Update status to RUNNING
        job.status = ImportJobStatus.RUNNING

        # Parse CSV
        parser = CSVParser(schema)
        mapper = RowMapper(schema)
        validator = QuestionValidator(schema, db)
        writer = QuestionWriter(db, current_user.id)

        accepted = []
        rejected = []
        error_counts: dict[str, int] = {}

        for row_number, raw_row in parser.parse(file_content):
            # Map to canonical fields
            canonical = mapper.map_row(raw_row)

            # Validate
            errors = validator.validate(canonical)

            if errors:
                # Rejected
                rejected_row = ImportJobRow(
                    job_id=job.id,
                    row_number=row_number,
                    external_id=canonical.get("external_id"),
                    raw_row_json=raw_row,
                    errors_json=[e.to_dict() for e in errors],
                )
                db.add(rejected_row)
                rejected.append(rejected_row)

                # Count errors
                for error in errors:
                    error_counts[error.code] = error_counts.get(error.code, 0) + 1
            else:
                # Accepted
                accepted.append(canonical)

        # Insert accepted questions (unless dry run)
        if not dry_run and accepted:
            inserted_count = writer.bulk_insert(accepted)
        else:
            inserted_count = 0

        # Update job stats
        job.total_rows = len(accepted) + len(rejected)
        job.accepted_rows = len(accepted)
        job.rejected_rows = len(rejected)
        job.summary_json = {"error_counts": error_counts, "dry_run": dry_run}
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

    except Exception as e:
        job.status = ImportJobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    """Download rejected rows as CSV."""
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

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="job_{job_id}_rejected.csv"'},
    )
