"""Security endpoints for CSP reporting and other security features."""

import json
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.logging import get_logger
from app.core.rate_limit import get_client_ip
from app.security.rate_limit import rate_limit_ip
from app.models.csp_report import CSPReport

logger = get_logger(__name__)

router = APIRouter(prefix="/security", tags=["Security"])


class CSPReportRequest(BaseModel):
    """CSP violation report payload (CSP reporting API format)."""

    # CSP report format: https://www.w3.org/TR/CSP3/#reporting
    # Note: Browsers send this as {"csp-report": {...}} or just the report object
    csp_report: dict[str, Any] = Field(..., description="CSP violation report object", alias="csp-report")
    
    class Config:
        populate_by_name = True  # Allow both "csp-report" and "csp_report"


@router.post(
    "/csp-report",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CSP violation report",
    description="Collect Content-Security-Policy violation reports (rate-limited, sampled).",
    dependencies=[
        Depends(rate_limit_ip("security.csp_report", fail_open=True)),
    ],
)
async def csp_report(
    request_data: CSPReportRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """
    Collect CSP violation reports.
    
    This endpoint accepts CSP violation reports from browsers and stores
    them (sampled) for analysis. Rate-limited to prevent abuse.
    """
    # Extract report data
    report = request_data.csp_report
    
    # Extract metadata
    document_uri = report.get("document-uri") or report.get("documentUri")
    referrer = report.get("referrer")
    blocked_uri = report.get("blocked-uri") or report.get("blockedUri")
    violated_directive = report.get("violated-directive") or report.get("violatedDirective")
    effective_directive = report.get("effective-directive") or report.get("effectiveDirective")
    original_policy = report.get("original-policy") or report.get("originalPolicy")
    
    # Extract source location if available
    source_file = None
    line_number = None
    column_number = None
    if "source-file" in report:
        source_file = report.get("source-file")
        line_number = str(report.get("line-number", ""))
        column_number = str(report.get("column-number", ""))
    elif "sourceFile" in report:
        source_file = report.get("sourceFile")
        line_number = str(report.get("lineNumber", ""))
        column_number = str(report.get("columnNumber", ""))
    
    # Get request metadata
    user_agent = request.headers.get("user-agent")
    ip_address = get_client_ip(request)
    
    # Simple sampling: store all reports for now (can be adjusted later)
    # In production, you might want to sample 1% or use time-based sampling
    sampled = "true"
    
    # Create report record
    csp_report = CSPReport(
        document_uri=document_uri,
        referrer=referrer,
        blocked_uri=blocked_uri,
        violated_directive=violated_directive,
        effective_directive=effective_directive,
        original_policy=original_policy,
        source_file=source_file,
        line_number=line_number if line_number else None,
        column_number=column_number if column_number else None,
        user_agent=user_agent,
        ip_address=ip_address,
        sampled=sampled,
    )
    
    db.add(csp_report)
    
    try:
        db.commit()
        logger.info(
            f"CSP violation reported: {violated_directive} blocked {blocked_uri} on {document_uri}",
            extra={
                "violated_directive": violated_directive,
                "blocked_uri": blocked_uri,
                "document_uri": document_uri,
            },
        )
    except Exception as e:
        db.rollback()
        # Log error but don't fail the request (CSP reports should be fire-and-forget)
        logger.error(f"Failed to store CSP report: {e}", exc_info=True)
    
    # Always return 204 (no content) - CSP reports are fire-and-forget
    return None
