"""Runtime control framework: resolver, police-mode, freeze, audit, snapshot, registry."""

from app.runtime_control.audit import append_switch_audit
from app.runtime_control.contracts import ModuleKey, ResolvedRuntime
from app.runtime_control.freeze import require_mutations_allowed
from app.runtime_control.police import (
    phrase_for_flag,
    phrase_for_profile,
    require_confirmation,
)
from app.runtime_control.resolver import refresh_runtime_cache, resolve_runtime
from app.runtime_control.registry import bridge_state, get_impl, register
from app.runtime_control.snapshot import build_and_store_snapshot

__all__ = [
    "ModuleKey",
    "ResolvedRuntime",
    "resolve_runtime",
    "refresh_runtime_cache",
    "require_confirmation",
    "phrase_for_flag",
    "phrase_for_profile",
    "require_mutations_allowed",
    "append_switch_audit",
    "build_and_store_snapshot",
    "register",
    "get_impl",
    "bridge_state",
]
