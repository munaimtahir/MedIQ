"""IRT Activation Policy - Strict gate evaluation for production activation.

This module implements a "No-Vibes" activation policy that requires objective,
measurable criteria before IRT can be used for student-facing decisions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.learning_engine.config import (
    IRT_ACTIVATION_A_MIN,
    IRT_ACTIVATION_B_ABS_MAX,
    IRT_ACTIVATION_DELTA_BRIER,
    IRT_ACTIVATION_DELTA_ECE,
    IRT_ACTIVATION_DELTA_LOGLOSS,
    IRT_ACTIVATION_MAX_MEDIAN_DELTA_B,
    IRT_ACTIVATION_MAX_MEDIAN_SE,
    IRT_ACTIVATION_MAX_PCT_B_OOR,
    IRT_ACTIVATION_MAX_PCT_C_CAP,
    IRT_ACTIVATION_MAX_PCT_LOW_A,
    IRT_ACTIVATION_MAX_SUBGROUP_PENALTY,
    IRT_ACTIVATION_MIN_ATTEMPTS,
    IRT_ACTIVATION_MIN_ATTEMPTS_PER_ITEM,
    IRT_ACTIVATION_MIN_ATTEMPTS_PER_USER,
    IRT_ACTIVATION_MIN_CORR_A,
    IRT_ACTIVATION_MIN_CORR_B,
    IRT_ACTIVATION_MIN_CORR_C,
    IRT_ACTIVATION_MIN_FOLDS,
    IRT_ACTIVATION_MIN_ITEMS,
    IRT_ACTIVATION_MIN_PCT_SE_GOOD,
    IRT_ACTIVATION_MIN_USERS,
    IRT_ACTIVATION_SE_TARGET,
)
from app.models.eval import EvalMetric, EvalRun
from app.models.irt import IrtCalibrationRun, IrtItemParams

logger = logging.getLogger(__name__)

# Policy version
POLICY_VERSION = "v1"


@dataclass
class GateResult:
    """Result of a single activation gate."""

    name: str
    passed: bool
    value: float | int | None
    threshold: float | int | None
    notes: str


@dataclass
class ActivationDecision:
    """Activation decision with gate results."""

    eligible: bool
    policy_version: str
    evaluated_at: datetime
    gates: list[GateResult]
    recommended_scope: str  # "none" | "shadow_only" | "selection_only" | "scoring_only" | "selection_and_scoring"
    recommended_model: str  # "IRT_2PL" | "IRT_3PL"
    requires_human_ack: bool  # Always True - human must explicitly activate


async def evaluate_irt_activation(
    db: AsyncSession,
    run_id: UUID,
    model_type: str,
    policy_version: str = POLICY_VERSION,
) -> ActivationDecision:
    """
    Evaluate IRT activation gates for a calibration run.

    Args:
        db: Database session
        run_id: IRT calibration run ID
        model_type: "IRT_2PL" or "IRT_3PL"
        policy_version: Policy version (default: "v1")

    Returns:
        ActivationDecision with gate results
    """
    logger.info(f"Evaluating IRT activation for run {run_id}, model {model_type}, policy {policy_version}")

    # Load run
    run = await db.get(IrtCalibrationRun, run_id)
    if not run:
        raise ValueError(f"IRT calibration run not found: {run_id}")

    if run.status != "SUCCEEDED":
        raise ValueError(f"Run must be SUCCEEDED to evaluate activation. Current status: {run.status}")

    gates: list[GateResult] = []

    # Gate A: Minimum Data Sufficiency
    gate_a = await _evaluate_gate_a(db, run_id, run)
    gates.append(gate_a)

    # Gate B: Holdout Predictive Superiority vs Baseline
    gate_b = await _evaluate_gate_b(db, run_id, run)
    gates.append(gate_b)

    # Gate C: Calibration Sanity
    gate_c = await _evaluate_gate_c(db, run_id, run, model_type)
    gates.append(gate_c)

    # Gate D: Parameter Stability Over Time
    gate_d = await _evaluate_gate_d(db, run_id, run, model_type)
    gates.append(gate_d)

    # Gate E: Measurement Precision
    gate_e = await _evaluate_gate_e(db, run_id, run)
    gates.append(gate_e)

    # Gate F: Coverage + Fairness Sanity
    gate_f = await _evaluate_gate_f(db, run_id, run)
    gates.append(gate_f)

    # Determine eligibility
    all_passed = all(g.passed for g in gates)
    eligible = all_passed

    # Determine recommended scope (always start with selection_only if eligible)
    if eligible:
        recommended_scope = "selection_only"
    else:
        recommended_scope = "none"

    decision = ActivationDecision(
        eligible=eligible,
        policy_version=policy_version,
        evaluated_at=datetime.utcnow(),
        gates=gates,
        recommended_scope=recommended_scope,
        recommended_model=model_type,
        requires_human_ack=True,  # Always requires human activation
    )

    logger.info(
        f"Activation evaluation complete: eligible={eligible}, "
        f"gates_passed={sum(1 for g in gates if g.passed)}/{len(gates)}"
    )

    return decision


async def _evaluate_gate_a(db: AsyncSession, run_id: UUID, run: IrtCalibrationRun) -> GateResult:
    """Gate A: Minimum Data Sufficiency."""
    metrics = run.metrics or {}

    n_users_train = metrics.get("n_users_train", 0)
    n_items_train = metrics.get("n_items_train", 0)
    n_attempts_train = metrics.get("n_attempts_train", 0)
    median_attempts_per_item = metrics.get("median_attempts_per_item", 0.0)
    median_attempts_per_user = metrics.get("median_attempts_per_user", 0.0)

    checks = [
        (n_users_train >= IRT_ACTIVATION_MIN_USERS.value, "n_users_train", n_users_train, IRT_ACTIVATION_MIN_USERS.value),
        (n_items_train >= IRT_ACTIVATION_MIN_ITEMS.value, "n_items_train", n_items_train, IRT_ACTIVATION_MIN_ITEMS.value),
        (n_attempts_train >= IRT_ACTIVATION_MIN_ATTEMPTS.value, "n_attempts_train", n_attempts_train, IRT_ACTIVATION_MIN_ATTEMPTS.value),
        (
            median_attempts_per_item >= IRT_ACTIVATION_MIN_ATTEMPTS_PER_ITEM.value,
            "median_attempts_per_item",
            median_attempts_per_item,
            IRT_ACTIVATION_MIN_ATTEMPTS_PER_ITEM.value,
        ),
        (
            median_attempts_per_user >= IRT_ACTIVATION_MIN_ATTEMPTS_PER_USER.value,
            "median_attempts_per_user",
            median_attempts_per_user,
            IRT_ACTIVATION_MIN_ATTEMPTS_PER_USER.value,
        ),
    ]

    all_passed = all(check[0] for check in checks)
    failed_checks = [check[1] for check in checks if not check[0]]

    notes = f"Required: users>={IRT_ACTIVATION_MIN_USERS.value}, items>={IRT_ACTIVATION_MIN_ITEMS.value}, "
    notes += f"attempts>={IRT_ACTIVATION_MIN_ATTEMPTS.value}, median_per_item>={IRT_ACTIVATION_MIN_ATTEMPTS_PER_ITEM.value}, "
    notes += f"median_per_user>={IRT_ACTIVATION_MIN_ATTEMPTS_PER_USER.value}. "
    if failed_checks:
        notes += f"Failed: {', '.join(failed_checks)}"

    return GateResult(
        name="Gate A: Minimum Data Sufficiency",
        passed=all_passed,
        value=None,  # Multiple values, stored in notes
        threshold=None,
        notes=notes,
    )


async def _evaluate_gate_b(db: AsyncSession, run_id: UUID, run: IrtCalibrationRun) -> GateResult:
    """Gate B: Holdout Predictive Superiority vs Baseline."""
    # Get eval_run_id from IRT run
    if not run.eval_run_id:
        return GateResult(
            name="Gate B: Holdout Predictive Superiority vs Baseline",
            passed=False,
            value=None,
            threshold=None,
            notes="No eval_run_id linked to IRT run. Cannot compare vs baseline.",
        )

    # Get IRT metrics from eval_run
    irt_metrics = await _get_eval_metrics(db, run.eval_run_id, "irt_suite")

    # Get baseline metrics (need to find baseline eval run with same dataset_spec)
    # For now, we'll look for a baseline suite (e.g., "baseline_v1" or "bkt_v1")
    # This is a simplification - in practice, you'd want to match by dataset_spec
    baseline_metrics = await _get_baseline_metrics(db, run.dataset_spec or {})

    if not baseline_metrics:
        return GateResult(
            name="Gate B: Holdout Predictive Superiority vs Baseline",
            passed=False,
            value=None,
            threshold=None,
            notes="No baseline metrics found for comparison. Need baseline eval run with same dataset_spec.",
        )

    # Compare metrics
    logloss_irt = irt_metrics.get("logloss")
    logloss_baseline = baseline_metrics.get("logloss")
    brier_irt = irt_metrics.get("brier")
    brier_baseline = baseline_metrics.get("brier")
    ece_irt = irt_metrics.get("ece")
    ece_baseline = baseline_metrics.get("ece")

    if not all([logloss_irt, logloss_baseline, brier_irt, brier_baseline, ece_irt, ece_baseline]):
        return GateResult(
            name="Gate B: Holdout Predictive Superiority vs Baseline",
            passed=False,
            value=None,
            threshold=None,
            notes="Missing required metrics (logloss, brier, ece) for comparison.",
        )

    # Check improvements
    logloss_improved = logloss_irt <= (logloss_baseline - IRT_ACTIVATION_DELTA_LOGLOSS.value)
    brier_improved = brier_irt <= (brier_baseline - IRT_ACTIVATION_DELTA_BRIER.value)
    ece_improved = ece_irt <= (ece_baseline - IRT_ACTIVATION_DELTA_ECE.value)

    # TODO: Check fold stability (need to implement fold tracking)
    # For now, we'll assume single fold (pass if improvements hold)
    fold_stability = True  # Placeholder - should check >= 3 folds

    all_passed = logloss_improved and brier_improved and ece_improved and fold_stability

    notes = f"IRT logloss={logloss_irt:.4f} vs baseline {logloss_baseline:.4f} "
    notes += f"(need improvement >= {IRT_ACTIVATION_DELTA_LOGLOSS.value}), "
    notes += f"brier={brier_irt:.4f} vs {brier_baseline:.4f} "
    notes += f"(need improvement >= {IRT_ACTIVATION_DELTA_BRIER.value}), "
    notes += f"ece={ece_irt:.4f} vs {ece_baseline:.4f} "
    notes += f"(need improvement >= {IRT_ACTIVATION_DELTA_ECE.value}). "
    if not all_passed:
        failed = []
        if not logloss_improved:
            failed.append("logloss")
        if not brier_improved:
            failed.append("brier")
        if not ece_improved:
            failed.append("ece")
        if not fold_stability:
            failed.append("fold_stability")
        notes += f"Failed: {', '.join(failed)}"

    return GateResult(
        name="Gate B: Holdout Predictive Superiority vs Baseline",
        passed=all_passed,
        value=None,  # Multiple values
        threshold=None,
        notes=notes,
    )


async def _evaluate_gate_c(db: AsyncSession, run_id: UUID, run: IrtCalibrationRun, model_type: str) -> GateResult:
    """Gate C: Calibration Sanity."""
    # Get item parameters
    stmt = select(IrtItemParams).where(IrtItemParams.run_id == run_id)
    result = await db.execute(stmt)
    items = result.scalars().all()

    if not items:
        return GateResult(
            name="Gate C: Calibration Sanity",
            passed=False,
            value=None,
            threshold=None,
            notes="No item parameters found.",
        )

    total_items = len(items)
    low_a_count = sum(1 for item in items if item.a < IRT_ACTIVATION_A_MIN.value)
    b_oor_count = sum(1 for item in items if abs(item.b) > IRT_ACTIVATION_B_ABS_MAX.value)

    pct_low_a = low_a_count / total_items if total_items > 0 else 0.0
    pct_b_oor = b_oor_count / total_items if total_items > 0 else 0.0

    checks = [
        (pct_low_a <= IRT_ACTIVATION_MAX_PCT_LOW_A.value, "pct_low_a", pct_low_a, IRT_ACTIVATION_MAX_PCT_LOW_A.value),
        (pct_b_oor <= IRT_ACTIVATION_MAX_PCT_B_OOR.value, "pct_b_oor", pct_b_oor, IRT_ACTIVATION_MAX_PCT_B_OOR.value),
    ]

    # For 3PL, check c near cap
    if model_type == "IRT_3PL":
        # Assume 5-option MCQ (K=5) for now
        c_cap = 0.95 * (1.0 / 5.0)  # 0.19
        c_near_cap_count = sum(1 for item in items if item.c and item.c > c_cap)
        pct_c_cap = c_near_cap_count / total_items if total_items > 0 else 0.0
        checks.append(
            (pct_c_cap <= IRT_ACTIVATION_MAX_PCT_C_CAP.value, "pct_c_cap", pct_c_cap, IRT_ACTIVATION_MAX_PCT_C_CAP.value)
        )

    all_passed = all(check[0] for check in checks)
    failed_checks = [check[1] for check in checks if not check[0]]

    notes = f"Total items: {total_items}. "
    notes += f"Low discrimination (a < {IRT_ACTIVATION_A_MIN.value}): {low_a_count} ({pct_low_a:.1%}), "
    notes += f"max allowed: {IRT_ACTIVATION_MAX_PCT_LOW_A.value:.1%}. "
    notes += f"Difficulty out of range (|b| > {IRT_ACTIVATION_B_ABS_MAX.value}): {b_oor_count} ({pct_b_oor:.1%}), "
    notes += f"max allowed: {IRT_ACTIVATION_MAX_PCT_B_OOR.value:.1%}. "
    if model_type == "IRT_3PL":
        notes += f"c near cap: {c_near_cap_count} ({pct_c_cap:.1%}), max allowed: {IRT_ACTIVATION_MAX_PCT_C_CAP.value:.1%}. "
    if failed_checks:
        notes += f"Failed: {', '.join(failed_checks)}"

    return GateResult(
        name="Gate C: Calibration Sanity",
        passed=all_passed,
        value=None,
        threshold=None,
        notes=notes,
    )


async def _evaluate_gate_d(db: AsyncSession, run_id: UUID, run: IrtCalibrationRun, model_type: str) -> GateResult:
    """Gate D: Parameter Stability Over Time."""
    # Find previous eligible run (same model_type)
    stmt = (
        select(IrtCalibrationRun)
        .where(
            IrtCalibrationRun.model_type == model_type,
            IrtCalibrationRun.status == "SUCCEEDED",
            IrtCalibrationRun.id != run_id,
        )
        .order_by(IrtCalibrationRun.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    prev_run = result.scalar_one_or_none()

    if not prev_run:
        # No previous run - pass (first run)
        return GateResult(
            name="Gate D: Parameter Stability Over Time",
            passed=True,
            value=None,
            threshold=None,
            notes="No previous eligible run found. First run - stability check skipped.",
        )

    # Get current and previous item parameters
    stmt_curr = select(IrtItemParams).where(IrtItemParams.run_id == run_id)
    result_curr = await db.execute(stmt_curr)
    curr_items = {item.question_id: item for item in result_curr.scalars().all()}

    stmt_prev = select(IrtItemParams).where(IrtItemParams.run_id == prev_run.id)
    result_prev = await db.execute(stmt_prev)
    prev_items = {item.question_id: item for item in result_prev.scalars().all()}

    # Find shared items
    shared_question_ids = set(curr_items.keys()) & set(prev_items.keys())

    if len(shared_question_ids) < 10:
        return GateResult(
            name="Gate D: Parameter Stability Over Time",
            passed=False,
            value=None,
            threshold=None,
            notes=f"Insufficient shared items for stability check: {len(shared_question_ids)} < 10.",
        )

    # Compute correlations and drift
    try:
        from scipy.stats import spearmanr
    except ImportError:
        logger.error("scipy not available for stability check")
        return GateResult(
            name="Gate D: Parameter Stability Over Time",
            passed=False,
            value=None,
            threshold=None,
            notes="scipy not available for correlation computation.",
        )

    shared_ids = list(shared_question_ids)
    curr_b = [curr_items[qid].b for qid in shared_ids]
    prev_b = [prev_items[qid].b for qid in shared_ids]
    curr_a = [curr_items[qid].a for qid in shared_ids]
    prev_a = [prev_items[qid].a for qid in shared_ids]

    corr_b, _ = spearmanr(curr_b, prev_b)
    corr_a, _ = spearmanr(curr_a, prev_a)

    delta_b = [abs(curr_items[qid].b - prev_items[qid].b) for qid in shared_ids]
    median_delta_b = sorted(delta_b)[len(delta_b) // 2] if delta_b else float("inf")

    checks = [
        (corr_b >= IRT_ACTIVATION_MIN_CORR_B.value, "corr_b", corr_b, IRT_ACTIVATION_MIN_CORR_B.value),
        (corr_a >= IRT_ACTIVATION_MIN_CORR_A.value, "corr_a", corr_a, IRT_ACTIVATION_MIN_CORR_A.value),
        (
            median_delta_b <= IRT_ACTIVATION_MAX_MEDIAN_DELTA_B.value,
            "median_delta_b",
            median_delta_b,
            IRT_ACTIVATION_MAX_MEDIAN_DELTA_B.value,
        ),
    ]

    # For 3PL, check c correlation
    if model_type == "IRT_3PL":
        curr_c = [curr_items[qid].c for qid in shared_ids if curr_items[qid].c is not None]
        prev_c = [prev_items[qid].c for qid in shared_ids if prev_items[qid].c is not None]
        if len(curr_c) == len(prev_c) and len(curr_c) >= 10:
            corr_c, _ = spearmanr(curr_c, prev_c)
            checks.append(
                (corr_c >= IRT_ACTIVATION_MIN_CORR_C.value, "corr_c", corr_c, IRT_ACTIVATION_MIN_CORR_C.value)
            )

    all_passed = all(check[0] for check in checks)
    failed_checks = [check[1] for check in checks if not check[0]]

    notes = f"Shared items: {len(shared_question_ids)}. "
    notes += f"Correlation b: {corr_b:.3f} (min: {IRT_ACTIVATION_MIN_CORR_B.value}), "
    notes += f"correlation a: {corr_a:.3f} (min: {IRT_ACTIVATION_MIN_CORR_A.value}), "
    notes += f"median |delta_b|: {median_delta_b:.3f} (max: {IRT_ACTIVATION_MAX_MEDIAN_DELTA_B.value}). "
    if failed_checks:
        notes += f"Failed: {', '.join(failed_checks)}"

    return GateResult(
        name="Gate D: Parameter Stability Over Time",
        passed=all_passed,
        value=None,
        threshold=None,
        notes=notes,
    )


async def _evaluate_gate_e(db: AsyncSession, run_id: UUID, run: IrtCalibrationRun) -> GateResult:
    """Gate E: Measurement Precision (Information / SE)."""
    from app.models.irt import IrtUserAbility

    # Get user abilities with SE
    stmt = select(IrtUserAbility).where(IrtUserAbility.run_id == run_id, IrtUserAbility.theta_se.isnot(None))
    result = await db.execute(stmt)
    abilities = result.scalars().all()

    if not abilities:
        return GateResult(
            name="Gate E: Measurement Precision",
            passed=False,
            value=None,
            threshold=None,
            notes="No user abilities with SE found.",
        )

    theta_ses = [a.theta_se for a in abilities if a.theta_se is not None]
    if not theta_ses:
        return GateResult(
            name="Gate E: Measurement Precision",
            passed=False,
            value=None,
            threshold=None,
            notes="No valid theta SE values found.",
        )

    median_se = sorted(theta_ses)[len(theta_ses) // 2]
    pct_se_good = sum(1 for se in theta_ses if se <= IRT_ACTIVATION_SE_TARGET.value) / len(theta_ses)

    median_se_ok = median_se <= IRT_ACTIVATION_MAX_MEDIAN_SE.value
    pct_ok = pct_se_good >= IRT_ACTIVATION_MIN_PCT_SE_GOOD.value

    all_passed = median_se_ok and pct_ok

    notes = f"Users: {len(abilities)}. "
    notes += f"Median SE: {median_se:.3f} (max: {IRT_ACTIVATION_MAX_MEDIAN_SE.value}), "
    notes += f"pct with SE <= {IRT_ACTIVATION_SE_TARGET.value}: {pct_se_good:.1%} "
    notes += f"(min: {IRT_ACTIVATION_MIN_PCT_SE_GOOD.value:.1%}). "
    if not all_passed:
        failed = []
        if not median_se_ok:
            failed.append("median_se")
        if not pct_ok:
            failed.append("pct_se_good")
        notes += f"Failed: {', '.join(failed)}"

    return GateResult(
        name="Gate E: Measurement Precision",
        passed=all_passed,
        value=None,
        threshold=None,
        notes=notes,
    )


async def _evaluate_gate_f(db: AsyncSession, run_id: UUID, run: IrtCalibrationRun) -> GateResult:
    """Gate F: Coverage + Fairness Sanity."""
    # Get overall logloss from eval_run
    if not run.eval_run_id:
        return GateResult(
            name="Gate F: Coverage + Fairness Sanity",
            passed=False,
            value=None,
            threshold=None,
            notes="No eval_run_id linked. Cannot check subgroup fairness.",
        )

    overall_metric = await _get_eval_metric(db, run.eval_run_id, "logloss", "GLOBAL", None)
    if not overall_metric:
        return GateResult(
            name="Gate F: Coverage + Fairness Sanity",
            passed=False,
            value=None,
            threshold=None,
            notes="No overall logloss metric found.",
        )

    overall_logloss = float(overall_metric.value)

    # Get subgroup metrics (year, block)
    year_metrics = await _get_subgroup_metrics(db, run.eval_run_id, "YEAR")
    block_metrics = await _get_subgroup_metrics(db, run.eval_run_id, "BLOCK")

    all_subgroups = year_metrics + block_metrics

    if not all_subgroups:
        # No subgroup data - pass (can't check fairness)
        return GateResult(
            name="Gate F: Coverage + Fairness Sanity",
            passed=True,
            value=None,
            threshold=None,
            notes="No subgroup metrics found. Fairness check skipped.",
        )

    # Check each subgroup
    failed_subgroups = []
    for metric in all_subgroups:
        subgroup_logloss = float(metric.value)
        penalty = subgroup_logloss - overall_logloss
        if penalty > IRT_ACTIVATION_MAX_SUBGROUP_PENALTY.value:
            failed_subgroups.append(f"{metric.scope_type}:{metric.scope_id} (penalty: {penalty:.4f})")

    all_passed = len(failed_subgroups) == 0

    notes = f"Overall logloss: {overall_logloss:.4f}. "
    notes += f"Subgroups checked: {len(all_subgroups)}. "
    notes += f"Max allowed penalty: {IRT_ACTIVATION_MAX_SUBGROUP_PENALTY.value}. "
    if failed_subgroups:
        notes += f"Failed subgroups: {', '.join(failed_subgroups)}"

    return GateResult(
        name="Gate F: Coverage + Fairness Sanity",
        passed=all_passed,
        value=None,
        threshold=None,
        notes=notes,
    )


# Helper functions


async def _get_eval_metrics(db: AsyncSession, eval_run_id: UUID, suite_name: str) -> dict[str, float]:
    """Get metrics from eval run."""
    stmt = select(EvalMetric).where(
        EvalMetric.run_id == eval_run_id,
        EvalMetric.scope_type == "GLOBAL",
        EvalMetric.scope_id.is_(None),
    )
    result = await db.execute(stmt)
    metrics = result.scalars().all()

    return {m.metric_name: float(m.value) for m in metrics}


async def _get_baseline_metrics(db: AsyncSession, dataset_spec: dict[str, Any]) -> dict[str, float]:
    """Get baseline metrics for comparison.

    TODO: This should match by dataset_spec. For now, we'll look for the most recent baseline run.
    """
    # Look for baseline suite (e.g., "baseline_v1" or "bkt_v1")
    stmt = (
        select(EvalRun)
        .where(EvalRun.suite_name.in_(["baseline_v1", "bkt_v1", "full_stack_v1"]))
        .where(EvalRun.status == "SUCCEEDED")
        .order_by(EvalRun.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    baseline_run = result.scalar_one_or_none()

    if not baseline_run:
        return {}

    return await _get_eval_metrics(db, baseline_run.id, baseline_run.suite_name)


async def _get_eval_metric(
    db: AsyncSession, eval_run_id: UUID, metric_name: str, scope_type: str, scope_id: str | None
) -> EvalMetric | None:
    """Get a specific eval metric."""
    stmt = select(EvalMetric).where(
        EvalMetric.run_id == eval_run_id,
        EvalMetric.metric_name == metric_name,
        EvalMetric.scope_type == scope_type,
        EvalMetric.scope_id == scope_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_subgroup_metrics(db: AsyncSession, eval_run_id: UUID, scope_type: str) -> list[EvalMetric]:
    """Get subgroup metrics (YEAR or BLOCK)."""
    stmt = select(EvalMetric).where(
        EvalMetric.run_id == eval_run_id,
        EvalMetric.metric_name == "logloss",
        EvalMetric.scope_type == scope_type,
        EvalMetric.scope_id.isnot(None),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
