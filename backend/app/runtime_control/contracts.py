"""Runtime control typed contracts: module keys, resolved runtime."""

from enum import Enum
from typing import Any, TypedDict


class ModuleKey(str, Enum):
    """Module keys for version overrides and feature toggles."""

    MASTERY = "mastery"
    REVISION = "revision"
    ADAPTIVE = "adaptive"
    DIFFICULTY = "difficulty"
    MISTAKES = "mistakes"
    SEARCH = "search"
    GRAPH = "graph"
    WAREHOUSE = "warehouse"
    IRT = "irt"


class ResolvedRuntime(TypedDict, total=False):
    """Effective runtime: profile, modules, feature toggles, flags."""

    profile: str
    modules: dict[str, str]
    feature_toggles: dict[str, bool]
    freeze_updates: bool
    exam_mode: bool
    source: dict[str, Any]
