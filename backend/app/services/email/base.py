"""Base email provider interface."""

from abc import ABC, abstractmethod


class EmailProvider(ABC):
    """Base interface for email providers."""

    @abstractmethod
    def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        meta: dict | None = None,
    ) -> str:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body_text: Plain text email body
            body_html: Optional HTML email body
            meta: Optional metadata dict

        Returns:
            Provider message ID (e.g., "console:<uuid>", SMTP message ID, etc.)
        """
        pass
