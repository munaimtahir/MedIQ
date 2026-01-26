"""Email outbox service - provider-agnostic email queue."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.email.provider_factory import get_email_provider
from app.email.runtime import (
    EmailMode,
    get_effective_email_mode,
    get_email_runtime_config_sync,
)
from app.models.email import EmailOutbox, EmailStatus

logger = logging.getLogger(__name__)


def enqueue_email(
    db: Session,
    to_email: str,
    subject: str,
    template_key: str,
    template_vars: dict[str, Any],
    to_name: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
) -> EmailOutbox:
    """
    Enqueue an email to the outbox.

    Always writes to outbox. Status determined by effective email mode.

    Args:
        db: Database session
        to_email: Recipient email
        subject: Email subject
        template_key: Template identifier (e.g., "PASSWORD_RESET")
        template_vars: Template variables
        to_name: Optional recipient name
        body_text: Optional plain text body (if not using template)
        body_html: Optional HTML body (if not using template)

    Returns:
        EmailOutbox record
    """
    # Get runtime config
    runtime_cfg = get_email_runtime_config_sync(db)
    provider, provider_configured = get_email_provider()

    # Resolve effective mode
    effective_mode, warnings, blocking_reasons = get_effective_email_mode(
        requested_mode=runtime_cfg.requested_mode,
        email_freeze=runtime_cfg.email_freeze,
        provider_configured=provider_configured,
    )

    # Determine status
    if effective_mode == EmailMode.DISABLED:
        status = EmailStatus.BLOCKED_DISABLED.value
    elif effective_mode == EmailMode.SHADOW:
        status = EmailStatus.SHADOW_LOGGED.value
    else:  # ACTIVE
        status = EmailStatus.QUEUED.value

    # Create outbox record
    outbox = EmailOutbox(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        template_key=template_key,
        template_vars=template_vars,
        status=status,
        provider=provider.__class__.__name__.replace("EmailProvider", "").lower() if provider else None,
    )

    db.add(outbox)
    db.commit()
    db.refresh(outbox)

    if warnings:
        logger.warning(f"Email enqueued with warnings: {warnings}", extra={"email_id": str(outbox.id)})
    if blocking_reasons:
        logger.warning(f"Email blocked: {blocking_reasons}", extra={"email_id": str(outbox.id)})

    return outbox


def drain_outbox(db: Session, limit: int = 50) -> dict[str, Any]:
    """
    Drain email outbox - send queued emails.

    Only sends when effective_mode == ACTIVE.

    Args:
        db: Database session
        limit: Maximum number of emails to process (default 50, max 500)

    Returns:
        Summary dict with counts
    """
    if limit > 500:
        limit = 500

    # Check effective mode
    runtime_cfg = get_email_runtime_config_sync(db)
    provider, provider_configured = get_email_provider()

    effective_mode, _, _ = get_effective_email_mode(
        requested_mode=runtime_cfg.requested_mode,
        email_freeze=runtime_cfg.email_freeze,
        provider_configured=provider_configured,
    )

    if effective_mode != EmailMode.ACTIVE:
        logger.warning(f"Cannot drain outbox: effective mode is {effective_mode.value}, not ACTIVE")
        # Count queued emails that would be skipped
        queued_count = (
            db.query(EmailOutbox)
            .filter(EmailOutbox.status == EmailStatus.QUEUED.value)
            .count()
        )
        return {
            "attempted": 0,
            "sent": 0,
            "failed": 0,
            "skipped": min(queued_count, limit),
            "effective_mode": effective_mode.value,
        }

    if not provider:
        logger.warning("Cannot drain outbox: no provider available")
        return {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "No provider available",
        }

    # Get queued emails
    queued = (
        db.query(EmailOutbox)
        .filter(EmailOutbox.status == EmailStatus.QUEUED.value)
        .order_by(EmailOutbox.created_at)
        .limit(limit)
        .all()
    )

    sent_count = 0
    failed_count = 0

    for email in queued:
        try:
            # Mark as sending
            email.status = EmailStatus.SENDING.value
            email.attempts += 1
            email.updated_at = datetime.now(timezone.utc)
            db.commit()

            # Send via provider
            message_id = provider.send(
                to=email.to_email,
                subject=email.subject,
                body_text=email.body_text or "",
                body_html=email.body_html,
                meta={"template_key": email.template_key, "template_vars": email.template_vars},
            )

            # Mark as sent
            email.status = EmailStatus.SENT.value
            email.provider_message_id = message_id
            email.sent_at = datetime.now(timezone.utc)
            email.updated_at = datetime.now(timezone.utc)
            db.commit()

            sent_count += 1
            logger.info(f"Email sent successfully", extra={"email_id": str(email.id), "to": email.to_email})

        except Exception as e:
            error_msg = str(e)[:500]  # Truncate long errors
            email.status = EmailStatus.FAILED.value
            email.last_error = error_msg
            email.updated_at = datetime.now(timezone.utc)

            # Cap attempts at 5
            if email.attempts >= 5:
                logger.warning(
                    f"Email failed after {email.attempts} attempts, leaving as failed",
                    extra={"email_id": str(email.id), "to": email.to_email},
                )
            else:
                # Reset to queued for retry (will be picked up in next drain)
                email.status = EmailStatus.QUEUED.value

            db.commit()
            failed_count += 1
            logger.error(
                f"Failed to send email: {error_msg}",
                extra={"email_id": str(email.id), "to": email.to_email},
                exc_info=True,
            )

    return {
        "attempted": len(queued),
        "sent": sent_count,
        "failed": failed_count,
        "skipped": 0,
        "effective_mode": effective_mode.value,
    }
