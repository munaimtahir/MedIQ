"""
Learning Intelligence Engine Module.

This module contains all learning algorithm logic including:
- Mastery tracking
- Revision scheduling
- Difficulty adaptation
- Adaptive question selection
- Common mistakes identification

Each algorithm is versioned and parameterized independently.
"""

from app.learning_engine.constants import AlgoKey, AlgoStatus, RunStatus, RunTrigger
from app.learning_engine.registry import (
    get_active_algo_version,
    get_active_params,
    resolve_active,
)
from app.learning_engine.runs import log_run_failure, log_run_start, log_run_success

__all__ = [
    # Constants
    "AlgoKey",
    "AlgoStatus",
    "RunStatus",
    "RunTrigger",
    # Registry
    "get_active_algo_version",
    "get_active_params",
    "resolve_active",
    # Run logging
    "log_run_start",
    "log_run_success",
    "log_run_failure",
]
