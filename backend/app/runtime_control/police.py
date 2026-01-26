"""Police-mode confirmation phrases for runtime control actions."""

from typing import Callable

from fastapi import Request

from app.security.police_mode import validate_police_confirm

# Standard phrases per action (exact match required)
PHRASES: dict[str, str] = {
    "ENABLE_EXAM_MODE": "ENABLE EXAM MODE",
    "DISABLE_EXAM_MODE": "DISABLE EXAM MODE",
    "ENABLE_FREEZE_UPDATES": "ENABLE FREEZE UPDATES",
    "DISABLE_FREEZE_UPDATES": "DISABLE FREEZE UPDATES",
    "SET_PROFILE_PRIMARY": "SET PROFILE PRIMARY",
    "SET_PROFILE_FALLBACK": "SET PROFILE FALLBACK",
    "SET_PROFILE_SHADOW": "SET PROFILE SHADOW",
    "OVERRIDE_MODULE": "OVERRIDE MODULE",  # prefix; full phrase may include module/version
    "ENABLE_ELASTICSEARCH": "ENABLE ELASTICSEARCH",
    "DISABLE_ELASTICSEARCH": "DISABLE ELASTICSEARCH",
    "ENABLE_NEO4J": "ENABLE NEO4J",
    "DISABLE_NEO4J": "DISABLE NEO4J",
    "ENABLE_SNOWFLAKE_EXPORT": "ENABLE SNOWFLAKE EXPORT",
    "DISABLE_SNOWFLAKE_EXPORT": "DISABLE SNOWFLAKE EXPORT",
    "ENABLE_IRT_SHADOW": "ENABLE IRT SHADOW",
    "DISABLE_IRT_SHADOW": "DISABLE IRT SHADOW",
}


def require_confirmation(
    request: Request,
    confirmation_phrase: str,
    reason: str | None,
    expected_phrase: str,
) -> str:
    """
    Validate police-mode confirmation (phrase + reason).
    Wraps validate_police_confirm. Returns validated reason.
    """
    return validate_police_confirm(request, confirmation_phrase, reason, expected_phrase)


def phrase_for_flag(key: str, enabled: bool) -> str:
    """Return required phrase for toggling a flag (EXAM_MODE, FREEZE_UPDATES)."""
    if key == "EXAM_MODE":
        return PHRASES["ENABLE_EXAM_MODE"] if enabled else PHRASES["DISABLE_EXAM_MODE"]
    if key == "FREEZE_UPDATES":
        return PHRASES["ENABLE_FREEZE_UPDATES"] if enabled else PHRASES["DISABLE_FREEZE_UPDATES"]
    raise ValueError(f"Unknown flag: {key}")


def phrase_for_profile(profile_name: str) -> str:
    """Return required phrase for switching profile."""
    m = {
        "primary": PHRASES["SET_PROFILE_PRIMARY"],
        "fallback": PHRASES["SET_PROFILE_FALLBACK"],
        "shadow": PHRASES["SET_PROFILE_SHADOW"],
    }
    if profile_name not in m:
        raise ValueError(f"Unknown profile: {profile_name}")
    return m[profile_name]
