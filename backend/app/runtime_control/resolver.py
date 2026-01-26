"""RuntimeResolver: resolve effective runtime from flags, profile, overrides. Cached reads, safe fallback."""

import logging
import threading
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.runtime_control import ModuleOverride, RuntimeProfile
from app.runtime_control.contracts import ModuleKey, ResolvedRuntime
from app.system.flags import is_exam_mode, is_freeze_updates

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = int(getattr(settings, "SYSTEM_FLAGS_CACHE_TTL_SECONDS", 10))
_cache_lock = threading.Lock()
_cache: dict[str, Any] = {}
_cache_ts: datetime | None = None

# Default module versions per profile (primary=v1, fallback=v0)
DEFAULT_PRIMARY: dict[str, str] = {
    "mastery": "v1",
    "revision": "v1",
    "adaptive": "v1",
    "difficulty": "v1",
    "mistakes": "v1",
    "search": "v0",
    "graph": "v0",
    "warehouse": "v0",
    "irt": "v0",
}
DEFAULT_FALLBACK: dict[str, str] = {k: "v0" for k in DEFAULT_PRIMARY}
DEFAULT_SHADOW: dict[str, str] = {**DEFAULT_PRIMARY, "irt": "v0-shadow"}


def _is_cache_fresh() -> bool:
    if _cache_ts is None:
        return False
    age = (datetime.utcnow() - _cache_ts).total_seconds()
    return age < CACHE_TTL_SECONDS


def _get_profile_config(db: Session) -> tuple[str, dict[str, str]]:
    """Return (active_profile_name, config modules)."""
    try:
        active = db.query(RuntimeProfile).filter(RuntimeProfile.is_active.is_(True)).first()
        if active:
            cfg = active.config or {}
            mods = {k: str(v) for k, v in (cfg or {}).items() if isinstance(v, str)}
            defaults = DEFAULT_PRIMARY if active.name == "primary" else (
                DEFAULT_SHADOW if active.name == "shadow" else DEFAULT_FALLBACK
            )
            for k in ModuleKey:
                mods.setdefault(k.value, defaults.get(k.value, "v0"))
            return active.name, mods
        # No active profile -> primary defaults
        return "primary", dict(DEFAULT_PRIMARY)
    except Exception as e:
        logger.warning("RuntimeResolver: profile read failed: %s", e)
        raise


def _get_overrides(db: Session) -> dict[str, tuple[str, bool]]:
    """Return {module_key: (version_key, is_enabled)}."""
    try:
        rows = db.query(ModuleOverride).all()
        return {r.module_key: (r.version_key, r.is_enabled) for r in rows}
    except Exception as e:
        logger.warning("RuntimeResolver: overrides read failed: %s", e)
        return {}


def _resolve(
    db: Session,
    profile_name: str,
    profile_modules: dict[str, str],
    overrides: dict[str, tuple[str, bool]],
) -> ResolvedRuntime:
    """Merge profile + overrides -> effective modules and feature toggles."""
    modules = dict(profile_modules)
    feature_toggles: dict[str, bool] = {}
    for mk, (ver, enabled) in overrides.items():
        modules[mk] = ver
        feature_toggles[mk] = enabled
    # Infra toggles: search, graph, warehouse, irt — default off when v0
    for k in (ModuleKey.SEARCH, ModuleKey.GRAPH, ModuleKey.WAREHOUSE, ModuleKey.IRT):
        key = k.value
        if key not in feature_toggles:
            feature_toggles[key] = (modules.get(key) or "v0") != "v0"
    return ResolvedRuntime(
        profile=profile_name,
        modules=modules,
        feature_toggles=feature_toggles,
        freeze_updates=is_freeze_updates(db),
        exam_mode=is_exam_mode(db),
        source={"profile": profile_name, "overrides": list(overrides.keys())},
    )


def _conservative_fallback() -> ResolvedRuntime:
    """Safe state when DB unavailable: fallback profile, freeze_updates true."""
    return ResolvedRuntime(
        profile="fallback",
        modules=dict(DEFAULT_FALLBACK),
        feature_toggles={k.value: False for k in ModuleKey},
        freeze_updates=True,
        exam_mode=False,
        source={"fallback": "db_unavailable"},
    )


def resolve_runtime(db: Session | None = None, use_cache: bool = True) -> ResolvedRuntime:
    """
    Resolve current effective runtime (flags, profile, overrides).
    Cached TTL 5–10s. On DB failure, returns last known or conservative fallback.
    Never raises.
    """
    global _cache_ts

    if use_cache and _is_cache_fresh():
        with _cache_lock:
            if _cache:
                return ResolvedRuntime(**_cache)

    if db is None:
        if not use_cache:
            return _conservative_fallback()
        with _cache_lock:
            if _cache:
                return ResolvedRuntime(**_cache)
        return _conservative_fallback()

    try:
        profile_name, profile_modules = _get_profile_config(db)
        overrides = _get_overrides(db)
        resolved = _resolve(db, profile_name, profile_modules, overrides)
        with _cache_lock:
            _cache.clear()
            _cache.update(resolved)
            _cache_ts = datetime.utcnow()
        return resolved
    except Exception as e:
        logger.warning("RuntimeResolver: resolve failed, using fallback: %s", e)
        with _cache_lock:
            if _cache:
                return ResolvedRuntime(**_cache)
        return _conservative_fallback()


def refresh_runtime_cache(db: Session) -> ResolvedRuntime:
    """Force refresh resolver cache from DB."""
    global _cache_ts
    _cache_ts = None
    return resolve_runtime(db, use_cache=False)
