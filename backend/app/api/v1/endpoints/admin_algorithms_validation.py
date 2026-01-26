"""
Validation helpers for algorithm runtime confirmation phrases.
"""

from typing import Literal


def validate_confirmation_phrase(
    action_type: Literal[
        "PROFILE_SWITCH",
        "FREEZE",
        "UNFREEZE",
        "OVERRIDES_APPLY",
        "SEARCH_ENGINE_SWITCH",
        "RANKING_GO_ACTIVE",
        "RANKING_GO_SHADOW",
        "RANKING_PYTHON",
        "RANKING_DISABLED",
        "RANKING_COMPUTE",
    ],
    phrase: str | None,
    target_profile: str | None = None,
    target_mode: str | None = None,
) -> tuple[bool, str | None]:
    """
    Validate confirmation phrase matches required phrase for action.

    Args:
        action_type: Type of action being performed
        phrase: Confirmation phrase provided by user
        target_profile: Target profile (required for PROFILE_SWITCH)
        target_mode: Target search engine mode (required for SEARCH_ENGINE_SWITCH)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phrase:
        return False, "confirmation_phrase is required"

    phrase_upper = phrase.strip().upper()

    if action_type == "PROFILE_SWITCH":
        if not target_profile:
            return False, "target_profile is required for PROFILE_SWITCH"
        if target_profile == "V1_PRIMARY":
            required = "SWITCH TO V1_PRIMARY"
        elif target_profile == "V0_FALLBACK":
            required = "SWITCH TO V0_FALLBACK"
        else:
            return False, f"Invalid target_profile: {target_profile}"
    elif action_type == "FREEZE":
        required = "FREEZE UPDATES"
    elif action_type == "UNFREEZE":
        required = "UNFREEZE UPDATES"
    elif action_type == "OVERRIDES_APPLY":
        required = "APPLY OVERRIDES"
    elif action_type == "SEARCH_ENGINE_SWITCH":
        if not target_mode:
            return False, "target_mode is required for SEARCH_ENGINE_SWITCH"
        if target_mode == "postgres":
            required = "SWITCH SEARCH TO POSTGRES"
        elif target_mode == "elasticsearch":
            required = "SWITCH SEARCH TO ELASTICSEARCH"
        else:
            return False, f"Invalid target_mode: {target_mode}"
    elif action_type == "RANKING_GO_ACTIVE":
        required = "SWITCH RANKING TO GO ACTIVE"
    elif action_type == "RANKING_GO_SHADOW":
        required = "SWITCH RANKING TO GO SHADOW"
    elif action_type == "RANKING_PYTHON":
        required = "SWITCH RANKING TO PYTHON"
    elif action_type == "RANKING_DISABLED":
        required = "SWITCH RANKING TO DISABLED"
    elif action_type == "RANKING_COMPUTE":
        required = "RUN RANKING COMPUTE"
    else:
        return False, f"Unknown action_type: {action_type}"

    if phrase_upper != required.upper():
        return False, f"Confirmation phrase mismatch. Expected: {required}, got: {phrase}"

    return True, None
