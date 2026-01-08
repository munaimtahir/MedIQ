"""Tests for email service."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.email.console import ConsoleEmailProvider
from app.services.email.service import get_email_service, send_email
from app.services.email.smtp import SMTPEmailProvider


def test_console_provider_sends_email(caplog):
    """Test that console provider logs email."""
    provider = ConsoleEmailProvider()
    provider.send(
        to="test@example.com",
        subject="Test Subject",
        body_text="Test body",
        body_html="<p>Test body</p>",
    )
    # Check that email was logged
    assert "test@example.com" in caplog.text or "Test Subject" in caplog.text


def test_smtp_provider_initialization():
    """Test SMTP provider initialization."""
    provider = SMTPEmailProvider(
        host="localhost",
        port=1025,
        from_email="test@example.com",
        use_tls=False,
        use_ssl=False,
    )
    assert provider.host == "localhost"
    assert provider.port == 1025
    assert provider.from_email == "test@example.com"


@patch("app.services.email.service._email_service", None)
def test_get_email_service_console():
    """Test that console provider is selected when EMAIL_BACKEND=console."""
    with patch.dict(os.environ, {"EMAIL_BACKEND": "console"}):
        # Reload settings
        from app.core.config import Settings
        test_settings = Settings()
        with patch("app.services.email.service.settings", test_settings):
            service = get_email_service()
            assert isinstance(service, ConsoleEmailProvider)


@patch("app.services.email.service._email_service", None)
def test_get_email_service_mailpit():
    """Test that SMTP provider is selected when EMAIL_BACKEND=mailpit."""
    with patch.dict(os.environ, {"EMAIL_BACKEND": "mailpit"}):
        from app.core.config import Settings
        test_settings = Settings()
        with patch("app.services.email.service.settings", test_settings):
            service = get_email_service()
            assert isinstance(service, SMTPEmailProvider)


@patch("app.services.email.service.get_email_service")
def test_send_email_calls_provider(mock_get_service):
    """Test that send_email calls the email service."""
    mock_provider = MagicMock()
    mock_get_service.return_value = mock_provider

    send_email(
        to="test@example.com",
        subject="Test",
        body_text="Body",
    )

    mock_provider.send.assert_called_once_with(
        to="test@example.com",
        subject="Test",
        body_text="Body",
        body_html=None,
    )


@patch("smtplib.SMTP")
def test_smtp_provider_send_success(mock_smtp):
    """Test SMTP provider sends email successfully."""
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server

    provider = SMTPEmailProvider(
        host="localhost",
        port=1025,
        from_email="test@example.com",
        use_tls=False,
        use_ssl=False,
    )

    provider.send(
        to="recipient@example.com",
        subject="Test",
        body_text="Body",
        body_html="<p>Body</p>",
    )

    mock_smtp.assert_called_once_with("localhost", 1025)
    mock_server.send_message.assert_called_once()
    mock_server.quit.assert_called_once()


@patch("smtplib.SMTP")
@patch("app.services.email.smtp.logger")
def test_smtp_provider_fallback_on_error(mock_logger, mock_smtp):
    """Test SMTP provider falls back to console on error."""
    mock_smtp.side_effect = Exception("Connection failed")

    provider = SMTPEmailProvider(
        host="localhost",
        port=1025,
        from_email="test@example.com",
        use_tls=False,
        use_ssl=False,
    )

    # Should not raise, should fallback to console
    provider.send(
        to="recipient@example.com",
        subject="Test",
        body_text="Body",
    )

    # Verify fallback was called
    mock_logger.warning.assert_called()
    mock_logger.warning.assert_any_call("Falling back to console email provider")
