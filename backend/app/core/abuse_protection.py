"""Brute-force and abuse protection utilities."""

from fastapi import Request, status

from app.core.app_exceptions import raise_app_error
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import get_client_ip, normalize_email_for_key
from app.core.redis_client import get_redis_client
from app.core.security_logging import log_security_event

logger = get_logger(__name__)


def record_login_failure(email: str, ip: str) -> None:
    """Record a failed login attempt."""
    redis_client = get_redis_client()
    if redis_client is None:
        return

    try:
        email_normalized = normalize_email_for_key(email)
        email_key = f"fail:login:email:{email_normalized}"
        ip_key = f"fail:login:ip:{ip}"

        # Increment failure counters
        email_count = redis_client.incr(email_key)
        ip_count = redis_client.incr(ip_key)

        # Set expiry on first failure
        if email_count == 1:
            redis_client.expire(email_key, settings.LOGIN_FAIL_WINDOW)
        if ip_count == 1:
            redis_client.expire(ip_key, settings.LOGIN_FAIL_WINDOW)

        # Check if email lockout threshold reached
        if email_count >= settings.LOGIN_FAIL_EMAIL_THRESHOLD:
            lock_key = f"lock:email:{email_normalized}"
            redis_client.setex(lock_key, settings.EMAIL_LOCK_TTL, "1")
            logger.warning(
                "Email locked due to repeated failures",
                extra={
                    "event_type": "account_locked",
                    "email": email_normalized,
                    "failure_count": email_count,
                    "lock_ttl": settings.EMAIL_LOCK_TTL,
                },
            )

        # Check if IP lockout threshold reached
        if ip_count >= settings.LOGIN_FAIL_IP_THRESHOLD:
            lock_key = f"lock:ip:{ip}"
            lock_ttl = settings.IP_LOCK_TTL

            # Escalation: if IP was already locked, increase TTL
            if settings.IP_LOCK_ESCALATION:
                existing_lock = redis_client.get(lock_key)
                if existing_lock:
                    current_ttl = redis_client.ttl(lock_key)
                    if current_ttl > 0:
                        # Escalate: multiply TTL, cap at max
                        lock_ttl = min(current_ttl * 2, settings.IP_LOCK_MAX_TTL)

            redis_client.setex(lock_key, lock_ttl, "1")
            logger.warning(
                "IP locked due to repeated failures",
                extra={
                    "event_type": "ip_locked",
                    "ip": ip,
                    "failure_count": ip_count,
                    "lock_ttl": lock_ttl,
                },
            )

    except Exception as e:
        logger.error(f"Failed to record login failure: {e}", exc_info=True)


def clear_login_failures(email: str, ip: str) -> None:
    """Clear failure counters on successful login."""
    redis_client = get_redis_client()
    if redis_client is None:
        return

    try:
        email_normalized = normalize_email_for_key(email)
        email_key = f"fail:login:email:{email_normalized}"
        ip_key = f"fail:login:ip:{ip}"

        redis_client.delete(email_key)
        redis_client.delete(ip_key)
    except Exception as e:
        logger.error(f"Failed to clear login failures: {e}", exc_info=True)


def check_email_locked(email: str, request: Request) -> None:
    """Check if email is locked and raise if so."""
    redis_client = get_redis_client()
    if redis_client is None:
        return

    try:
        email_normalized = normalize_email_for_key(email)
        lock_key = f"lock:email:{email_normalized}"
        lock_exists = redis_client.exists(lock_key)

        if lock_exists:
            ttl = redis_client.ttl(lock_key)

            log_security_event(
                request,
                event_type="account_locked",
                outcome="deny",
                reason_code="ACCOUNT_LOCKED",
            )

            raise_app_error(
                status_code=status.HTTP_403_FORBIDDEN,
                code="ACCOUNT_LOCKED",
                message="Account temporarily locked due to repeated failed login attempts.",
                details={"lock_expires_in": ttl},
            )
    except Exception as e:
        logger.error(f"Failed to check email lock: {e}", exc_info=True)
        # On error, don't block (fail open if Redis fails)


def check_ip_locked(ip: str, request: Request) -> None:
    """Check if IP is locked and raise if so."""
    redis_client = get_redis_client()
    if redis_client is None:
        return

    try:
        lock_key = f"lock:ip:{ip}"
        lock_exists = redis_client.exists(lock_key)

        if lock_exists:
            ttl = redis_client.ttl(lock_key)

            log_security_event(
                request,
                event_type="ip_locked",
                outcome="deny",
                reason_code="IP_LOCKED",
            )

            raise_app_error(
                status_code=status.HTTP_403_FORBIDDEN,
                code="IP_LOCKED",
                message="IP address temporarily locked due to repeated abuse.",
                details={"lock_expires_in": ttl},
            )
    except Exception as e:
        logger.error(f"Failed to check IP lock: {e}", exc_info=True)
        # On error, don't block (fail open if Redis fails)

