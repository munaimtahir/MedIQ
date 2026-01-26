"""Email provider factory."""

from app.core.config import settings
from app.core.logging import get_logger
from app.services.email.base import EmailProvider
from app.services.email.console import ConsoleEmailProvider
from app.services.email.smtp import SMTPEmailProvider

logger = get_logger(__name__)


def get_email_provider() -> tuple[EmailProvider | None, bool]:
    """
    Get email provider based on configuration.

    Returns:
        Tuple of (provider_instance, is_configured)
    """
    provider_type = settings.EMAIL_PROVIDER.lower() if hasattr(settings, "EMAIL_PROVIDER") else "console"

    if provider_type == "console":
        return ConsoleEmailProvider(), True

    if provider_type == "smtp":
        # Check if SMTP config is available
        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
        smtp_from_email = settings.SMTP_FROM_EMAIL

        if not smtp_host or not smtp_port or not smtp_from_email:
            logger.warning("SMTP provider requested but configuration incomplete, falling back to console")
            return ConsoleEmailProvider(), False

        try:
            provider = SMTPEmailProvider(
                host=smtp_host,
                port=int(smtp_port),
                from_email=smtp_from_email,
                use_tls=settings.SMTP_USE_TLS,
                use_ssl=settings.SMTP_USE_SSL,
            )
            return provider, True
        except Exception as e:
            logger.error(f"Failed to initialize SMTP provider: {e}", exc_info=True)
            return ConsoleEmailProvider(), False

    # Default to console
    logger.warning(f"Unknown email provider type: {provider_type}, falling back to console")
    return ConsoleEmailProvider(), False
