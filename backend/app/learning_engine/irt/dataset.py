"""IRT dataset extraction from attempt logs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import numpy as np
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_cms import Question, QuestionStatus
from app.models.session import SessionAnswer, SessionMode, TestSession

logger = logging.getLogger(__name__)


@dataclass
class IRTRow:
    """Single IRT observation."""

    user_id: UUID
    question_id: UUID
    correct: int  # 0 or 1
    timestamp: datetime
    mode: str | None  # TUTOR, EXAM
    option_count: int  # 1..5 for MCQ; used to cap c at 1/K


class IRTDatasetSpec(BaseModel):
    """Dataset specification for IRT calibration."""

    time_min: datetime
    time_max: datetime
    years: list[int] | None = None
    block_ids: list[int] | None = None
    theme_ids: list[int] | None = None
    modes_included: list[str] | None = None  # ["TUTOR", "EXAM"] or ["EXAM"] only
    min_attempt_quality: dict[str, Any] | None = None  # e.g. exclude changed_count > N
    split_strategy: str = "time"
    split_config: dict[str, Any] | None = None
    seed: int = 42


def _option_count(question: Question | None) -> int:
    """Derive option_count from question. Default 5 for MCQ."""
    if not question:
        return 5
    count = 0
    for opt in (question.option_a, question.option_b, question.option_c, question.option_d, question.option_e):
        if opt is not None and str(opt).strip():
            count += 1
    return max(1, count) if count else 5


async def build_irt_dataset(
    db: AsyncSession,
    spec: IRTDatasetSpec,
) -> tuple[list[IRTRow], list[IRTRow]]:
    """
    Build IRT dataset (train, val) from attempt logs.

    - Prefer exam-like attempts if modes_included restricts to EXAM.
    - Exclude attempts for unpublished/disabled items (status != PUBLISHED).
    - Exclude attempts with missing answers (selected_index is None).
    - Deterministic split via spec.seed; dataset_spec stored in run.
    """
    logger.info("Building IRT dataset: %s to %s", spec.time_min, spec.time_max)

    stmt = (
        select(
            SessionAnswer.question_id,
            SessionAnswer.is_correct,
            SessionAnswer.answered_at,
            SessionAnswer.changed_count,
            TestSession.user_id,
            TestSession.mode,
        )
        .join(TestSession, SessionAnswer.session_id == TestSession.id)
        .where(
            and_(
                SessionAnswer.answered_at >= spec.time_min,
                SessionAnswer.answered_at <= spec.time_max,
                SessionAnswer.selected_index.isnot(None),
            )
        )
    )
    if spec.years:
        stmt = stmt.where(TestSession.year.in_(spec.years))
    if spec.modes_included:
        mode_vals = []
        for m in spec.modes_included:
            s = str(m).upper()
            if s == "EXAM":
                mode_vals.append(SessionMode.EXAM)
            elif s == "TUTOR":
                mode_vals.append(SessionMode.TUTOR)
        if mode_vals:
            stmt = stmt.where(TestSession.mode.in_(mode_vals))

    stmt = stmt.order_by(TestSession.user_id, SessionAnswer.answered_at)
    result = await db.execute(stmt)
    rows = result.all()

    question_ids = list({r.question_id for r in rows})
    q_stmt = select(Question).where(
        Question.id.in_(question_ids),
        Question.status == QuestionStatus.PUBLISHED,
    )
    if spec.block_ids is not None:
        q_stmt = q_stmt.where(Question.block_id.in_(spec.block_ids))
    if spec.theme_ids is not None:
        q_stmt = q_stmt.where(Question.theme_id.in_(spec.theme_ids))
    q_result = await db.execute(q_stmt)
    questions = {q.id: q for q in q_result.scalars().all()}

    min_quality = spec.min_attempt_quality or {}
    max_changed = min_quality.get("max_changed_count")

    out: list[IRTRow] = []
    for r in rows:
        if r.question_id not in questions:
            continue
        if max_changed is not None and (r.changed_count or 0) > max_changed:
            continue
        q = questions[r.question_id]
        correct = 1 if r.is_correct else 0
        mode = r.mode.name if hasattr(r.mode, "name") else str(r.mode) if r.mode else None
        ts = r.answered_at
        if ts is None:
            continue
        out.append(
            IRTRow(
                user_id=r.user_id,
                question_id=r.question_id,
                correct=correct,
                timestamp=ts,
                mode=mode,
                option_count=_option_count(q),
            )
        )

    logger.info("IRT dataset: %d rows (published only)", len(out))

    # Deterministic split
    rng = np.random.default_rng(spec.seed)
    idx = np.arange(len(out))
    rng.shuffle(idx)
    split_cfg = spec.split_config or {}
    train_ratio = split_cfg.get("train_ratio", 0.8)
    split_i = int(len(out) * train_ratio)
    train_idx = sorted(idx[:split_i])
    val_idx = sorted(idx[split_i:])
    train = [out[i] for i in train_idx]
    val = [out[i] for i in val_idx]
    return train, val
