"""Console email provider (fallback for local dev)."""

from typing import Optional

from app.core.logging import get_logger
from app.services.email.base import EmailProvider

logger = get_logger(__name__)


class ConsoleEmailProvider(EmailProvider):
    """Console email provider - logs emails to console/logs."""

    def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> None:
        """Log email to console."""
        logger.info(
            "EMAIL (Console Provider)",
            extra={
                "email_to": to,
                "email_subject": subject,
                "email_body_text": body_text,
                "email_body_html": body_html,
            },
        )
        # Also print to console for visibility
        print("\n" + "=" * 80)
        print("EMAIL (Console Provider)")
        print("=" * 80)
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print("-" * 80)
        print("Body (Text):")
        print(body_text)
        if body_html:
            print("-" * 80)
            print("Body (HTML):")
            print(body_html)
        print("=" * 80 + "\n")
