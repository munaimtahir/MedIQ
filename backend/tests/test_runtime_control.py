"""Tests for runtime control: resolver, audit, snapshot, freeze."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.runtime_control import RuntimeProfile, SwitchAuditLog
from app.runtime_control import (
    append_switch_audit,
    phrase_for_flag,
    phrase_for_profile,
    refresh_runtime_cache,
    resolve_runtime,
)
from app.runtime_control.registry import bridge_state, get_impl, register


def _has_runtime_tables(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1 FROM runtime_profiles LIMIT 1"))
        return True
    except Exception:
        return False


def test_resolver_returns_defaults(db: Session) -> None:
    """Resolver returns primary profile defaults when runtime tables exist."""
    if not _has_runtime_tables(db):
        pytest.skip("runtime_profiles not present (migrations not applied)")
    r = resolve_runtime(db, use_cache=False)
    assert r.get("profile") in ("primary", "fallback", "shadow")
    assert "modules" in r
    mods = r["modules"]
    assert "mastery" in mods
    assert mods.get("mastery") in ("v0", "v1")
    assert "freeze_updates" in r
    assert "exam_mode" in r


def test_phrase_for_flag() -> None:
    """Police-mode phrases for EXAM_MODE and FREEZE_UPDATES."""
    assert phrase_for_flag("EXAM_MODE", True) == "ENABLE EXAM MODE"
    assert phrase_for_flag("EXAM_MODE", False) == "DISABLE EXAM MODE"
    assert phrase_for_flag("FREEZE_UPDATES", True) == "ENABLE FREEZE UPDATES"
    assert phrase_for_flag("FREEZE_UPDATES", False) == "DISABLE FREEZE UPDATES"
    with pytest.raises(ValueError, match="Unknown flag"):
        phrase_for_flag("UNKNOWN", True)


def test_phrase_for_profile() -> None:
    """Police-mode phrases for profile switch."""
    assert phrase_for_profile("primary") == "SET PROFILE PRIMARY"
    assert phrase_for_profile("fallback") == "SET PROFILE FALLBACK"
    assert phrase_for_profile("shadow") == "SET PROFILE SHADOW"
    with pytest.raises(ValueError, match="Unknown profile"):
        phrase_for_profile("invalid")


def test_append_switch_audit(db: Session) -> None:
    """Append switch audit writes a row (no commit)."""
    if not _has_runtime_tables(db):
        pytest.skip("switch_audit_log not present")
    before = db.query(SwitchAuditLog).count()
    append_switch_audit(
        db,
        actor_user_id=None,
        action_type="TEST_ACTION",
        before={"a": 1},
        after={"a": 2},
        reason="test",
    )
    db.commit()
    after = db.query(SwitchAuditLog).count()
    assert after == before + 1


def test_bridge_state_stub() -> None:
    """Bridge state stub is no-op."""
    assert bridge_state("mastery", "v0", "v1", "user-1") is True


def test_registry_stub() -> None:
    """Registry register/get_impl."""
    register("mastery", "v1", type("V1Impl", (), {}))
    assert get_impl("mastery", "v1") is not None
    assert get_impl("mastery", "v0") is None
    assert get_impl("unknown", "v1") is None


def test_resolve_runtime_no_db_returns_fallback() -> None:
    """Resolver with no DB returns conservative fallback."""
    r = resolve_runtime(db=None, use_cache=False)
    assert r.get("profile") == "fallback"
    assert r.get("freeze_updates") is True
    assert r.get("exam_mode") is False
