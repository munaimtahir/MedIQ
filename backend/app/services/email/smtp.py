"""SMTP email provider."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.logging import get_logger
from app.services.email.base import EmailProvider

logger = get_logger(__name__)


class SMTPEmailProvider(EmailProvider):
    """SMTP email provider."""

    def __init__(
        self,
        host: str,
        port: int,
        from_email: str,
        use_tls: bool = False,
        use_ssl: bool = False,
    ):
        """
        Initialize SMTP provider.

        Args:
            host: SMTP server host
            port: SMTP server port
            from_email: From email address
            use_tls: Use TLS
            use_ssl: Use SSL
        """
        self.host = host
        self.port = port
        self.from_email = from_email
        self.use_tls = use_tls
        self.use_ssl = use_ssl

    def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
    ) -> None:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to
            msg["Subject"] = subject

            # Add text and HTML parts
            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            # Connect and send
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port)
            else:
                server = smtplib.SMTP(self.host, self.port)

            if self.use_tls:
                server.starttls()

            # No authentication needed for Mailpit
            server.send_message(msg)
            server.quit()

            logger.info(
                f"Email sent successfully to {to}", extra={"email_to": to, "email_subject": subject}
            )
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}", exc_info=True)
            raise
