"""Test Package endpoints for offline mobile caching."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.etag import check_if_none_match, compute_etag, create_not_modified_response
from app.models.question_cms import Question, QuestionStatus
from app.models.test_package import PackageScope, TestPackage
from app.models.user import User
from app.schemas.test_package import (
    PackageScopeData,
    QuestionSnapshot,
    TestPackageListItem,
    TestPackageListResponse,
    TestPackageOut,
)

router = APIRouter(prefix="/tests/packages", tags=["Test Packages"])


@router.get("", response_model=TestPackageListResponse)
async def list_packages(
    scope: str | None = Query(None, description="Filter by scope (PROGRAM, YEAR, BLOCK, THEME)"),
    year_id: int | None = Query(None, description="Filter by year_id"),
    block_id: int | None = Query(None, description="Filter by block_id"),
    theme_id: int | None = Query(None, description="Filter by theme_id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestPackageListResponse:
    """
    List available test packages for offline download.
    
    Returns published packages only, with metadata for client caching decisions.
    """
    query = db.query(TestPackage).filter(TestPackage.is_published.is_(True))
    
    # Apply scope filter
    if scope:
        try:
            scope_enum = PackageScope(scope)
            query = query.filter(TestPackage.scope == scope_enum.value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}. Must be one of: PROGRAM, YEAR, BLOCK, THEME",
            )
    
    # Apply scope data filters (JSONB filtering)
    if year_id:
        query = query.filter(TestPackage.scope_data["year_id"].astext == str(year_id))
    if block_id:
        query = query.filter(TestPackage.scope_data["block_id"].astext == str(block_id))
    if theme_id:
        query = query.filter(TestPackage.scope_data["theme_id"].astext == str(theme_id))
    
    # Order by updated_at desc
    packages = query.order_by(TestPackage.updated_at.desc()).all()
    
    items = []
    for pkg in packages:
        scope_data = PackageScopeData(
            year_id=pkg.scope_data.get("year_id"),
            block_id=pkg.scope_data.get("block_id"),
            theme_id=pkg.scope_data.get("theme_id"),
        )
        items.append(
            TestPackageListItem(
                package_id=pkg.id,
                name=pkg.name,
                scope=pkg.scope,
                scope_data=scope_data,
                version=pkg.version,
                version_hash=pkg.version_hash,
                updated_at=pkg.updated_at or pkg.created_at,
            )
        )
    
    return TestPackageListResponse(items=items)


@router.get("/{package_id}")
async def get_package(
    package_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Get full test package for offline download.
    
    Supports ETag/If-None-Match for efficient caching.
    Returns 304 Not Modified if package unchanged.
    """
    package = db.query(TestPackage).filter(
        TestPackage.id == package_id,
        TestPackage.is_published.is_(True),
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found or not published",
        )
    
    # Compute ETag from version_hash
    etag = f'W/"{package.version_hash}"'
    
    # Check If-None-Match
    if check_if_none_match(request, etag):
        return create_not_modified_response(etag)
    
    # Build question snapshots
    questions = []
    for q_data in package.questions_json:
        questions.append(QuestionSnapshot(**q_data))
    
    scope_data = PackageScopeData(
        year_id=package.scope_data.get("year_id"),
        block_id=package.scope_data.get("block_id"),
        theme_id=package.scope_data.get("theme_id"),
    )
    
    response = TestPackageOut(
        package_id=package.id,
        name=package.name,
        description=package.description,
        scope=package.scope,
        scope_data=scope_data,
        version=package.version,
        version_hash=package.version_hash,
        questions=questions,
        created_at=package.created_at,
        updated_at=package.updated_at,
        published_at=package.published_at,
    )
    
    # Return JSON with ETag header
    import json
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        content=response.model_dump(),
        headers={"ETag": etag},
    )


@router.head("/{package_id}")
async def head_package(
    package_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    HEAD request for package (check ETag without downloading content).
    
    Returns 200 with ETag header, or 304 if If-None-Match matches.
    """
    package = db.query(TestPackage).filter(
        TestPackage.id == package_id,
        TestPackage.is_published.is_(True),
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found or not published",
        )
    
    etag = f'W/"{package.version_hash}"'
    
    if check_if_none_match(request, etag):
        return create_not_modified_response(etag)
    
    from fastapi.responses import Response
    
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"ETag": etag},
    )
