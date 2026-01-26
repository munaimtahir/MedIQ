"""Console email provider (fallback for local dev)."""

import uuid

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
        body_html: str | None = None,
        meta: dict | None = None,
    ) -> str:
        """Log email to console."""
        message_id = f"console:{uuid.uuid4()}"
        logger.info(
            "EMAIL (Console Provider)",
            extra={
                "email_to": to,
                "email_subject": subject,
                "email_body_text": body_text,
                "email_body_html": body_html,
                "message_id": message_id,
            },
        )
        # Also print to console for visibility
        print("\n" + "=" * 80)
        print("EMAIL (Console Provider)")
        print("=" * 80)
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"Message ID: {message_id}")
        print("-" * 80)
        print("Body (Text):")
        print(body_text)
        if body_html:
            print("-" * 80)
            print("Body (HTML):")
            print(body_html)
        print("=" * 80 + "\n")
        return message_id
