"""Base email provider interface."""

from abc import ABC, abstractmethod
from typing import Optional


class EmailProvider(ABC):
    """Base interface for email providers."""

    @abstractmethod
    def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> None:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body_text: Plain text email body
            body_html: Optional HTML email body
        """
        pass
