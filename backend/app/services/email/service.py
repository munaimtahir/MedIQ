"""Email service factory and main service."""

from app.core.config import settings
from app.core.logging import get_logger
from app.services.email.base import EmailProvider
from app.services.email.console import ConsoleEmailProvider
from app.services.email.smtp import SMTPEmailProvider

logger = get_logger(__name__)

# Global email service instance
_email_service: EmailProvider | None = None


def get_email_service() -> EmailProvider:
    """
    Get the email service provider.

    Returns:
        EmailProvider instance
    """
    global _email_service

    if _email_service is not None:
        return _email_service

    backend = getattr(settings, "EMAIL_BACKEND", "console").lower()

    if backend in ("mailpit", "smtp"):
        try:
            _email_service = SMTPEmailProvider(
                host=getattr(settings, "EMAIL_HOST", "localhost"),
                port=getattr(settings, "EMAIL_PORT", 1025),
                from_email=getattr(settings, "EMAIL_FROM", "noreply@local.test"),
                use_tls=getattr(settings, "EMAIL_USE_TLS", False),
                use_ssl=getattr(settings, "EMAIL_USE_SSL", False),
            )
            logger.info(
                f"Email service initialized: SMTP ({settings.EMAIL_HOST}:{settings.EMAIL_PORT})"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize SMTP email service, falling back to console: {e}")
            _email_service = ConsoleEmailProvider()
    else:
        _email_service = ConsoleEmailProvider()
        logger.info("Email service initialized: Console (fallback)")

    return _email_service


def send_email(
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> None:
    """
    Send an email using the configured email service.
    Falls back to console provider if SMTP fails.

    Args:
        to: Recipient email address
        subject: Email subject
        body_text: Plain text email body
        body_html: Optional HTML email body
    """
    service = get_email_service()
    try:
        service.send(to=to, subject=subject, body_text=body_text, body_html=body_html)
    except Exception as e:
        # If SMTP provider fails, fallback to console
        if isinstance(service, SMTPEmailProvider):
            logger.warning(f"SMTP email failed, falling back to console: {e}")
            console_provider = ConsoleEmailProvider()
            console_provider.send(to=to, subject=subject, body_text=body_text, body_html=body_html)
        else:
            # If already console or other error, re-raise
            raise
