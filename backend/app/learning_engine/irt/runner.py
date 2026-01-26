"""IRT calibration job runner."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import numpy as np
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.config import IRT_LOW_DISCRIMINATION_THRESHOLD
from app.learning_engine.eval.metrics.calibration import (
    brier_score,
    expected_calibration_error,
    log_loss,
    reliability_curve_data,
)
from app.learning_engine.eval.registry import (
    create_eval_run,
    save_curve,
    save_metric,
    update_eval_run_status,
)
from app.learning_engine.irt.dataset import IRTDatasetSpec, build_irt_dataset
from app.learning_engine.irt.fit import FitConfig, FitResult, fit_irt
from app.learning_engine.irt.prob import p_2pl, p_3pl
from app.learning_engine.irt.registry import (
    fetch_elo_difficulty_global,
    get_irt_artifact_path,
    get_irt_run,
    store_item_params,
    store_user_abilities,
    update_irt_run_status,
)
from app.jobs.lock import acquire_job_lock, release_job_lock

logger = logging.getLogger(__name__)


def _dataset_spec_from_run(run: Any) -> IRTDatasetSpec:
    spec = run.dataset_spec or {}
    tmin = spec.get("time_min")
    tmax = spec.get("time_max")
    if isinstance(tmin, str):
        tmin = datetime.fromisoformat(tmin.replace("Z", "+00:00"))
    if isinstance(tmax, str):
        tmax = datetime.fromisoformat(tmax.replace("Z", "+00:00"))
    return IRTDatasetSpec(
        time_min=tmin,
        time_max=tmax,
        years=spec.get("years"),
        block_ids=spec.get("block_ids"),
        theme_ids=spec.get("theme_ids"),
        modes_included=spec.get("modes_included"),
        min_attempt_quality=spec.get("min_attempt_quality"),
        split_strategy=spec.get("split_strategy", "time"),
        split_config=spec.get("split_config"),
        seed=run.seed,
    )


def _predict_val(
    val_rows: list[Any],
    res: FitResult,
    model_type: str,
) -> tuple[list[bool], list[float]]:
    y_true: list[bool] = []
    y_pred: list[float] = []
    for r in val_rows:
        th = res.user_theta.get(r.user_id, 0.0)
        a = res.item_a.get(r.question_id, 1.0)
        b = res.item_b.get(r.question_id, 0.0)
        c = res.item_c.get(r.question_id, 0.0)
        if model_type.upper() == "IRT_3PL":
            p = p_3pl(th, a, b, c)
        else:
            p = p_2pl(th, a, b)
        p = max(1e-15, min(1 - 1e-15, p))
        y_true.append(bool(r.correct))
        y_pred.append(p)
    return y_true, y_pred


def _info_curve_summary(res: FitResult, model_type: str) -> dict[str, Any]:
    """Grid of theta values and aggregate test information."""
    thetas = np.linspace(-3, 3, 31)
    info = np.zeros_like(thetas)
    for i, t in enumerate(thetas):
        for qid, a in res.item_a.items():
            b = res.item_b[qid]
            c = res.item_c.get(qid, 0.0)
            if model_type.upper() == "IRT_3PL":
                p = p_3pl(float(t), a, b, c)
            else:
                p = p_2pl(float(t), a, b)
            q = 1 - p
            info[i] += (a * a) * p * q
    return {
        "theta_grid": thetas.tolist(),
        "information": info.tolist(),
    }


def _item_flags(res: FitResult, model_type: str) -> dict[UUID, dict[str, Any]]:
    flags: dict[UUID, dict[str, Any]] = {}
    low_a = IRT_LOW_DISCRIMINATION_THRESHOLD.value
    for qid, a in res.item_a.items():
        f: dict[str, Any] = {}
        if a < low_a:
            f["low_discrimination"] = True
        flags[qid] = f
    return flags


async def run_irt_calibration(db: AsyncSession, run_id: UUID) -> None:
    """
    Run IRT calibration (respects freeze_updates mode).

    If freeze_updates is enabled, this will set status to "BLOCKED_FROZEN"
    and return without executing.
    """
    # Check freeze_updates mode
    from app.learning_engine.runtime import is_safe_mode_freeze_updates

    if await is_safe_mode_freeze_updates(db):
        logger.warning(f"IRT calibration run {run_id} blocked: freeze_updates is enabled")
        await update_irt_run_status(
            db,
            run_id,
            status="FAILED",
            error="Calibration blocked: freeze_updates mode is enabled. All learning state writes are paused.",
        )
        return

    # Continue with normal execution
    """
    Run IRT calibration for a given run_id.

    1. Mark run RUNNING; lock to prevent concurrent same-run execution.
    2. Build dataset; split train/val deterministically.
    3. Fit 2PL or 3PL.
    4. Compute val predictions; logloss, Brier, ECE.
    5. Stability (optional), info curve, item flags.
    6. Store params, abilities; metrics + artifact_paths; eval run.
    7. Mark SUCCEEDED or FAILED.
    """
    run = await get_irt_run(db, run_id)
    if not run:
        raise ValueError(f"IRT run not found: {run_id}")

    if run.status != "QUEUED":
        raise ValueError(f"IRT run {run_id} is not QUEUED (status={run.status})")

    lock_key = f"irt_calibration_{run_id}"
    if not await acquire_job_lock(db, lock_key, lock_duration_minutes=120):
        raise RuntimeError(f"Could not acquire lock for {lock_key}")

    started_at = datetime.now(timezone.utc)
    try:
        await update_irt_run_status(
            db, run_id, "RUNNING", started_at=started_at
        )

        spec = _dataset_spec_from_run(run)
        train, val = await build_irt_dataset(db, spec)
        if not train:
            raise ValueError("IRT dataset is empty")

        elo = await fetch_elo_difficulty_global(db)
        cfg = FitConfig()
        res = fit_irt(
            train,
            run.model_type,
            seed=run.seed,
            config=cfg,
            elo_difficulty=elo,
        )

        y_true, y_pred = _predict_val(val, res, run.model_type)
        n_bins = 10
        logloss_val = log_loss(y_true, y_pred)
        brier_val = brier_score(y_true, y_pred)
        ece_val, bin_details = expected_calibration_error(y_true, y_pred, n_bins)
        curve_data = reliability_curve_data(y_true, y_pred, n_bins)

        info_summary = _info_curve_summary(res, run.model_type)
        flags = _item_flags(res, run.model_type)

        metrics: dict[str, Any] = {
            "logloss": logloss_val,
            "brier": brier_val,
            "ece": ece_val,
            "n_train": len(train),
            "n_val": len(val),
            "stability": None,
            "info_curve_summary": info_summary,
            "calibration_bins": bin_details,
        }

        suite_name = "irt_2pl" if run.model_type == "IRT_2PL" else "irt_3pl"
        eval_run = await create_eval_run(
            db,
            suite_name=suite_name,
            suite_versions={"irt": "1.0"},
            dataset_spec=run.dataset_spec,
            config={"seed": run.seed, "n_bins": n_bins},
            random_seed=run.seed,
            notes=f"IRT calibration run {run_id}",
        )
        await update_eval_run_status(db, eval_run.id, "RUNNING")
        await save_metric(db, eval_run.id, "logloss", logloss_val, len(y_true))
        await save_metric(db, eval_run.id, "brier", brier_val, len(y_true))
        await save_metric(
            db, eval_run.id, "ece", ece_val, len(y_true),
            extra={"bin_details": bin_details},
        )
        await save_curve(db, eval_run.id, "reliability_curve_p_correct", curve_data)
        await update_eval_run_status(db, eval_run.id, "SUCCEEDED")

        item_c = res.item_c if run.model_type == "IRT_3PL" else {}
        item_c_se = res.item_c_se if run.model_type == "IRT_3PL" else {}
        await store_item_params(
            db,
            run_id,
            res.item_a,
            res.item_b,
            item_c,
            res.item_a_se,
            res.item_b_se,
            item_c_se,
            flags,
        )
        await store_user_abilities(
            db, run_id, res.user_theta, res.user_theta_se
        )

        art_path = get_irt_artifact_path(run_id)
        art_path.mkdir(parents=True, exist_ok=True)
        summary = {
            "run_id": str(run_id),
            "model_type": run.model_type,
            "metrics": metrics,
            "n_items": len(res.item_a),
            "n_users": len(res.user_theta),
        }
        summary_path = art_path / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        artifact_paths = {"summary_json": str(summary_path)}

        finished_at = datetime.now(timezone.utc)
        await update_irt_run_status(
            db,
            run_id,
            "SUCCEEDED",
            finished_at=finished_at,
            metrics=metrics,
            artifact_paths=artifact_paths,
            eval_run_id=eval_run.id,
        )
        logger.info("IRT calibration run %s succeeded", run_id)

    except Exception as e:
        logger.exception("IRT calibration run %s failed: %s", run_id, e)
        finished_at = datetime.now(timezone.utc)
        await update_irt_run_status(
            db,
            run_id,
            "FAILED",
            error=str(e),
            finished_at=finished_at,
        )
        raise
    finally:
        await release_job_lock(db, lock_key)
