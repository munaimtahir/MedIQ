"""Password reset email templates."""

from app.core.config import settings


def render_text(vars: dict) -> str:
    """
    Render password reset email text template.

    Args:
        vars: Template variables (reset_url, expires_minutes)

    Returns:
        Plain text email body
    """
    reset_url = vars.get("reset_url", "")
    expires_minutes = vars.get("expires_minutes", 30)

    return f"""You requested a password reset for your account.

Click the link below to reset your password:
{reset_url}

This link will expire in {expires_minutes} minutes.

If you did not request this reset, please ignore this email.

---
{settings.PROJECT_NAME}
"""


def render_html(vars: dict) -> str:
    """
    Render password reset email HTML template.

    Args:
        vars: Template variables (reset_url, expires_minutes)

    Returns:
        HTML email body
    """
    reset_url = vars.get("reset_url", "")
    expires_minutes = vars.get("expires_minutes", 30)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f4f4f4; padding: 20px; border-radius: 5px;">
        <h2 style="color: #333;">Password Reset Request</h2>
        <p>You requested a password reset for your account.</p>
        <p>
            <a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Reset Password
            </a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{reset_url}</p>
        <p style="color: #666; font-size: 0.9em;">This link will expire in {expires_minutes} minutes.</p>
        <p style="color: #666; font-size: 0.9em;">If you did not request this reset, please ignore this email.</p>
    </div>
    <p style="margin-top: 20px; color: #999; font-size: 0.8em;">
        ---<br>
        {settings.PROJECT_NAME}
    </p>
</body>
</html>
"""
