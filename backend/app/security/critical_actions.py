"""Critical action taxonomy and police-mode enforcement."""

from enum import Enum
from typing import Literal

# Critical audit events that require police-mode confirmation
CRITICAL_AUDIT_EVENTS = [
    "EMAIL_MODE_SWITCH",
    "EMAIL_OUTBOX_DRAIN",
    "NOTIFICATION_BROADCAST",
    "RANKING_MODE_SWITCH",
    "RANKING_COMPUTE",
    "WAREHOUSE_MODE_SWITCH",
    "SEARCH_MODE_SWITCH",
    "ALGO_MODE_SWITCH",
    "USER_ADMIN_UPDATE",
    "ADMIN_FREEZE_CHANGED",
    "EXAM_MODE_CHANGED",
]

# Mapping of critical events to required confirmation phrases
CRITICAL_PHRASES: dict[str, str] = {
    "EMAIL_MODE_SWITCH": "SWITCH EMAIL TO {mode}",  # Mode will be DISABLED/SHADOW/ACTIVE
    "EMAIL_OUTBOX_DRAIN": "DRAIN EMAIL OUTBOX",
    "NOTIFICATION_BROADCAST": "BROADCAST NOTIFICATION",
    "RANKING_MODE_SWITCH": "SWITCH RANKING TO {mode}",
    "RANKING_COMPUTE": "RUN RANKING COMPUTE",
    "WAREHOUSE_MODE_SWITCH": "SWITCH WAREHOUSE TO {mode}",
    "SEARCH_MODE_SWITCH": "SWITCH SEARCH TO {mode}",
    "ALGO_MODE_SWITCH": "SWITCH ALGO TO {mode}",
    "USER_ADMIN_UPDATE": "UPDATE ADMIN USER",
    "ADMIN_FREEZE_CHANGED": "SET ADMIN FREEZE",
}

# Critical endpoints that must include police-mode dependency
# Format: (endpoint_path, event_type, phrase_template)
CRITICAL_ENDPOINTS: list[tuple[str, str, str]] = [
    ("POST /v1/admin/email/runtime/switch", "EMAIL_MODE_SWITCH", "SWITCH EMAIL TO {mode}"),
    ("POST /v1/admin/email/outbox/drain", "EMAIL_OUTBOX_DRAIN", "DRAIN EMAIL OUTBOX"),
    ("POST /v1/admin/notifications/broadcast", "NOTIFICATION_BROADCAST", "BROADCAST NOTIFICATION"),
    ("POST /v1/admin/algorithms/runtime/switch", "ALGO_MODE_SWITCH", "SWITCH ALGO TO {mode}"),
    ("POST /v1/admin/security/freeze", "ADMIN_FREEZE_CHANGED", "SET ADMIN FREEZE"),
    # Add more as needed
]


class CriticalActionType(str, Enum):
    """Enum for critical action types."""

    EMAIL_MODE_SWITCH = "EMAIL_MODE_SWITCH"
    EMAIL_OUTBOX_DRAIN = "EMAIL_OUTBOX_DRAIN"
    NOTIFICATION_BROADCAST = "NOTIFICATION_BROADCAST"
    RANKING_MODE_SWITCH = "RANKING_MODE_SWITCH"
    RANKING_COMPUTE = "RANKING_COMPUTE"
    WAREHOUSE_MODE_SWITCH = "WAREHOUSE_MODE_SWITCH"
    SEARCH_MODE_SWITCH = "SEARCH_MODE_SWITCH"
    ALGO_MODE_SWITCH = "ALGO_MODE_SWITCH"
    USER_ADMIN_UPDATE = "USER_ADMIN_UPDATE"
    ADMIN_FREEZE_CHANGED = "ADMIN_FREEZE_CHANGED"
    EXAM_MODE_CHANGED = "EXAM_MODE_CHANGED"


def get_required_phrase(event_type: str, **kwargs: str) -> str:
    """
    Get required confirmation phrase for a critical event.
    
    Args:
        event_type: Critical event type
        **kwargs: Template variables (e.g., mode="ACTIVE")
    
    Returns:
        Required confirmation phrase
    """
    template = CRITICAL_PHRASES.get(event_type, "")
    if not template:
        raise ValueError(f"Unknown critical event type: {event_type}")
    
    # Replace template variables
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing template variable for {event_type}: {e}") from e


def is_critical_action(action: str) -> bool:
    """Check if an action is a critical action requiring police-mode."""
    return action in CRITICAL_AUDIT_EVENTS
