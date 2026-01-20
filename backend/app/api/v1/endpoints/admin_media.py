"""Admin media endpoints for question attachments."""

import hashlib
import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.question_cms import MediaAsset, MediaRole, Question, QuestionMedia, StorageProvider
from app.models.user import User, UserRole
from app.schemas.question_cms import MediaAttachIn, MediaOut

router = APIRouter(prefix="/admin/media", tags=["Admin - Media"])

# Storage directory for local files
STORAGE_DIR = Path("backend/storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "",
    response_model=MediaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload media",
    description="Upload a media file (image, etc.) for use in questions.",
)
async def upload_media(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> MediaOut:
    """Upload a media file."""
    # Validate file type (basic check - can be expanded)
    allowed_mime_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Allowed: {allowed_mime_types}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Calculate SHA256 for deduplication
    sha256_hash = hashlib.sha256(content).hexdigest()

    # Check if file already exists
    existing = db.query(MediaAsset).filter(MediaAsset.sha256 == sha256_hash).first()
    if existing:
        return MediaOut.model_validate(existing)

    # Generate file path
    file_ext = Path(file.filename).suffix if file.filename else ".bin"
    file_name = f"{sha256_hash[:16]}{file_ext}"
    file_path = STORAGE_DIR / file_name

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Create media asset record
    media_asset = MediaAsset(
        storage_provider=StorageProvider.LOCAL,
        path=str(file_path.relative_to(Path.cwd())),  # Relative path
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=file_size,
        sha256=sha256_hash,
        created_by=current_user.id,
    )

    db.add(media_asset)
    db.commit()
    db.refresh(media_asset)

    return MediaOut.model_validate(media_asset)


@router.get(
    "/{media_id}",
    response_model=MediaOut,
    summary="Get media",
    description="Get media asset information.",
)
async def get_media(
    media_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> MediaOut:
    """Get media asset information."""
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    return MediaOut.model_validate(media)


@router.post(
    "/questions/{question_id}/attach",
    response_model=dict,
    summary="Attach media to question",
    description="Attach an existing media asset to a question with a specific role.",
)
async def attach_media_to_question(
    question_id: UUID,
    attach_data: MediaAttachIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> dict:
    """Attach media to question."""
    # Verify question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Verify media exists
    media = db.query(MediaAsset).filter(MediaAsset.id == attach_data.media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    # Check if attachment already exists
    existing = (
        db.query(QuestionMedia)
        .filter(
            QuestionMedia.question_id == question_id,
            QuestionMedia.role == attach_data.role,
        )
        .first()
    )
    if existing:
        # Update existing attachment
        existing.media_id = attach_data.media_id
    else:
        # Create new attachment
        attachment = QuestionMedia(
            question_id=question_id,
            media_id=attach_data.media_id,
            role=attach_data.role,
        )
        db.add(attachment)

    db.commit()

    return {"message": "Media attached successfully", "question_id": str(question_id), "media_id": str(attach_data.media_id)}


@router.delete(
    "/questions/{question_id}/detach/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach media from question",
    description="Remove a media attachment from a question.",
)
async def detach_media_from_question(
    question_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> None:
    """Detach media from question."""
    attachment = (
        db.query(QuestionMedia)
        .filter(QuestionMedia.question_id == question_id, QuestionMedia.media_id == media_id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    db.delete(attachment)
    db.commit()
