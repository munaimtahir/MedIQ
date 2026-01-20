"""Constants for learning engine algorithms."""

from enum import Enum


class AlgoKey(str, Enum):
    """Algorithm identifier keys."""

    MASTERY = "mastery"
    REVISION = "revision"
    DIFFICULTY = "difficulty"
    ADAPTIVE = "adaptive"
    MISTAKES = "mistakes"


class AlgoStatus(str, Enum):
    """Algorithm version status."""

    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    EXPERIMENTAL = "EXPERIMENTAL"


class RunStatus(str, Enum):
    """Algorithm run execution status."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RunTrigger(str, Enum):
    """Algorithm run trigger source."""

    MANUAL = "manual"
    SUBMIT = "submit"
    NIGHTLY = "nightly"
    CRON = "cron"
    API = "api"
