"""Session runtime snapshot: capture at create, never change mid-session."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.runtime_control import SessionRuntimeSnapshot
from app.runtime_control.contracts import ResolvedRuntime
from app.runtime_control.resolver import resolve_runtime
from app.system.flags import is_exam_mode, is_freeze_updates


def build_and_store_snapshot(
    db: Session,
    session_id: UUID,
) -> ResolvedRuntime:
    """
    Resolve current runtime and store snapshot in session_runtime_snapshot.
    Call once at session creation. Does not update test_session; caller sets
    exam_mode_at_start / freeze_updates_at_start.
    """
    resolved = resolve_runtime(db, use_cache=False)
    profile = resolved.get("profile", "primary")
    modules = resolved.get("modules") or {}
    flags = {
        "exam_mode_at_start": is_exam_mode(db),
        "freeze_updates_at_start": is_freeze_updates(db),
    }

    snap = SessionRuntimeSnapshot(
        session_id=session_id,
        profile_name=profile,
        resolved_modules=modules,
        flags=flags,
    )
    db.add(snap)
    return resolved
