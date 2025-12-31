"""FastAPI dependencies for rate limiting."""

from fastapi import Depends, Request

from app.core.config import settings
from app.core.rate_limit import check_rate_limit_and_raise, get_client_ip, normalize_email_for_key


def require_rate_limit_login_ip(request: Request) -> None:
    """Rate limit dependency for login by IP."""
    ip = get_client_ip(request)
    key = f"rl:login:ip:{ip}"
    check_rate_limit_and_raise(
        key,
        settings.RL_LOGIN_IP_LIMIT,
        settings.RL_LOGIN_IP_WINDOW,
        request,
        event_type="rate_limited_login_ip",
    )


def require_rate_limit_login_email(email: str, request: Request) -> None:
    """Rate limit dependency for login by email."""
    email_normalized = normalize_email_for_key(email)
    key = f"rl:login:email:{email_normalized}"
    check_rate_limit_and_raise(
        key,
        settings.RL_LOGIN_EMAIL_LIMIT,
        settings.RL_LOGIN_EMAIL_WINDOW,
        request,
        event_type="rate_limited_login_email",
    )


def require_rate_limit_signup_ip(request: Request) -> None:
    """Rate limit dependency for signup by IP."""
    ip = get_client_ip(request)
    key = f"rl:signup:ip:{ip}"
    check_rate_limit_and_raise(
        key,
        settings.RL_SIGNUP_IP_LIMIT,
        settings.RL_SIGNUP_IP_WINDOW,
        request,
        event_type="rate_limited_signup_ip",
    )


def require_rate_limit_reset_ip(request: Request) -> None:
    """Rate limit dependency for password reset by IP."""
    ip = get_client_ip(request)
    key = f"rl:reset:ip:{ip}"
    check_rate_limit_and_raise(
        key,
        settings.RL_RESET_IP_LIMIT,
        settings.RL_RESET_IP_WINDOW,
        request,
        event_type="rate_limited_reset_ip",
    )


def require_rate_limit_reset_email(email: str, request: Request) -> None:
    """Rate limit dependency for password reset by email."""
    email_normalized = normalize_email_for_key(email)
    key = f"rl:reset:email:{email_normalized}"
    check_rate_limit_and_raise(
        key,
        settings.RL_RESET_EMAIL_LIMIT,
        settings.RL_RESET_EMAIL_WINDOW,
        request,
        event_type="rate_limited_reset_email",
    )


def require_rate_limit_refresh(user_id: str, request: Request) -> None:
    """Rate limit dependency for refresh token by user."""
    key = f"rl:refresh:user:{user_id}"
    check_rate_limit_and_raise(
        key,
        settings.RL_REFRESH_USER_LIMIT,
        settings.RL_REFRESH_USER_WINDOW,
        request,
        event_type="rate_limited_refresh",
    )

