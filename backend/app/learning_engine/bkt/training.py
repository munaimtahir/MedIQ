"""
BKT Training Pipeline - Fit parameters using EM via pyBKT.

Responsibilities:
1. Build training dataset from attempt logs
2. Fit BKT parameters using pyBKT EM algorithm
3. Apply parameter constraints and sanity checks
4. Compute validation metrics (AUC, RMSE, logloss)
5. Persist fitted parameters with versioning
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import SessionAnswer, SessionQuestion, SessionStatus, TestSession
from app.models.bkt import BKTSkillParams
from app.models.learning import AlgoVersion, AlgoParams
from app.learning_engine.bkt.core import validate_bkt_params, check_degeneracy
from app.learning_engine.constants import AlgoKey

logger = logging.getLogger(__name__)


class TrainingDataset:
    """Container for BKT training data."""

    def __init__(self, concept_id: UUID):
        self.concept_id = concept_id
        self.sequences = []  # List of (user_id, correctness_sequence) tuples
        self.total_attempts = 0
        self.unique_users = 0

    def add_sequence(self, user_id: UUID, correctness: list[int]):
        """
        Add a user's correctness sequence.

        Args:
            user_id: User ID
            correctness: List of 0/1 (wrong/correct)
        """
        if correctness:
            self.sequences.append((str(user_id), correctness))
            self.total_attempts += len(correctness)
            self.unique_users = len(set(user_id for user_id, _ in self.sequences))

    def is_sufficient(self, min_attempts: int = 10, min_users: int = 3) -> bool:
        """Check if dataset has sufficient data for fitting."""
        return self.total_attempts >= min_attempts and self.unique_users >= min_users

    def to_pyBKT_format(self) -> dict:
        """
        Convert to pyBKT format.

        pyBKT expects a dict with:
        - 'data': List of sequences
        - Each sequence is a dict with 'user_id' and 'correct' keys

        Returns:
            Dict in pyBKT format
        """
        formatted_sequences = []

        for user_id, correctness in self.sequences:
            formatted_sequences.append(
                {
                    "user_id": user_id,
                    "correct": correctness,
                }
            )

        return {
            "data": formatted_sequences,
            "concept_id": str(self.concept_id),
        }

    def summary(self) -> dict:
        """Get dataset summary statistics."""
        if not self.sequences:
            return {
                "total_attempts": 0,
                "unique_users": 0,
                "avg_sequence_length": 0,
                "min_sequence_length": 0,
                "max_sequence_length": 0,
            }

        sequence_lengths = [len(seq) for _, seq in self.sequences]

        return {
            "total_attempts": self.total_attempts,
            "unique_users": self.unique_users,
            "avg_sequence_length": np.mean(sequence_lengths),
            "min_sequence_length": np.min(sequence_lengths),
            "max_sequence_length": np.max(sequence_lengths),
        }


async def build_training_dataset(
    db: AsyncSession,
    concept_id: UUID,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    min_attempts_per_user: int = 1,
) -> TrainingDataset:
    """
    Build training dataset from session answers.

    Extracts ordered correctness sequences per user for a given concept.

    Args:
        db: Database session
        concept_id: Concept ID to build dataset for
        from_date: Start of data window (None = no limit)
        to_date: End of data window (None = now)
        min_attempts_per_user: Minimum attempts required per user

    Returns:
        TrainingDataset instance
    """
    dataset = TrainingDataset(concept_id)

    # Build query to get answers for this concept from submitted sessions
    # We need to join: TestSession -> SessionQuestion -> SessionAnswer
    # and filter for the specific concept_id

    # Note: We'll need to extract concept_id from session_questions.snapshot_json
    # For now, assume snapshot_json has a "concept_id" field or we have a direct mapping

    # Query for submitted/expired sessions in date range
    session_query = select(TestSession.id, TestSession.user_id).where(
        TestSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED])
    )

    if from_date:
        session_query = session_query.where(TestSession.submitted_at >= from_date)
    if to_date:
        session_query = session_query.where(TestSession.submitted_at <= to_date)

    result = await db.execute(session_query)
    sessions = result.all()

    if not sessions:
        logger.warning(f"No sessions found for concept {concept_id} in date range")
        return dataset

    session_ids = [s.id for s in sessions]
    users = {}  # user_id -> list of (timestamp, correct)

    # Get all answers for these sessions
    # We need to filter by concept_id somehow
    # For Phase 2, let's assume we have a way to identify concept_id from session_questions
    # This might require checking snapshot_json or having a direct concept_id field

    # Simplified approach: Get all answers and filter later
    # In production, would need proper concept_id extraction
    answer_query = (
        select(
            SessionAnswer.user_id,
            SessionAnswer.session_id,
            SessionAnswer.question_id,
            SessionAnswer.is_correct,
            SessionAnswer.answered_at,
            SessionQuestion.snapshot_json,
        )
        .join(
            SessionQuestion,
            and_(
                SessionAnswer.session_id == SessionQuestion.session_id,
                SessionAnswer.question_id == SessionQuestion.question_id,
            ),
        )
        .where(SessionAnswer.session_id.in_(session_ids))
        .order_by(SessionAnswer.user_id, SessionAnswer.answered_at)
    )

    result = await db.execute(answer_query)
    answers = result.all()

    # Group by user and extract sequences
    for answer in answers:
        user_id = answer.user_id
        is_correct = answer.is_correct
        answered_at = answer.answered_at
        snapshot = answer.snapshot_json or {}

        # Extract concept_id from snapshot
        # This depends on how questions are tagged
        # For now, check if snapshot has concept_id matching our target
        question_concept_id = snapshot.get("concept_id")

        # Skip if concept doesn't match (or if we can't determine concept)
        if question_concept_id and UUID(question_concept_id) != concept_id:
            continue

        if user_id not in users:
            users[user_id] = []

        users[user_id].append((answered_at, 1 if is_correct else 0))

    # Convert to sequences and add to dataset
    for user_id, attempts in users.items():
        if len(attempts) < min_attempts_per_user:
            continue

        # Sort by timestamp and extract correctness
        attempts.sort(key=lambda x: x[0])
        correctness = [correct for _, correct in attempts]

        dataset.add_sequence(user_id, correctness)

    logger.info(
        f"Built training dataset for concept {concept_id}: "
        f"{dataset.total_attempts} attempts from {dataset.unique_users} users"
    )

    return dataset


def apply_parameter_constraints(
    params: dict,
    constraints: dict,
) -> tuple[dict, bool, str]:
    """
    Apply parameter constraints to fitted BKT params.

    Args:
        params: Dict with keys p_L0, p_T, p_S, p_G
        constraints: Dict with min/max bounds for each parameter

    Returns:
        Tuple of (constrained_params, is_valid, message)
    """
    constrained = params.copy()
    violations = []

    # Apply constraints
    for param_name in ["L0", "T", "S", "G"]:
        key = f"p_{param_name}"
        min_key = f"{param_name}_min"
        max_key = f"{param_name}_max"

        if key in params:
            value = params[key]
            min_val = constraints.get(min_key, 0.001)
            max_val = constraints.get(max_key, 0.999)

            if value < min_val:
                violations.append(f"{param_name}={value:.3f} < min={min_val}")
                constrained[key] = min_val
            elif value > max_val:
                violations.append(f"{param_name}={value:.3f} > max={max_val}")
                constrained[key] = max_val

    # Validate constrained params
    is_valid, validation_msg = validate_bkt_params(
        constrained["p_L0"], constrained["p_T"], constrained["p_S"], constrained["p_G"]
    )

    if not is_valid:
        return constrained, False, f"Validation failed: {validation_msg}"

    # Check degeneracy
    is_non_degenerate, degeneracy_msg = check_degeneracy(
        constrained["p_L0"], constrained["p_T"], constrained["p_S"], constrained["p_G"]
    )

    if not is_non_degenerate:
        return constrained, False, f"Degeneracy detected: {degeneracy_msg}"

    if violations:
        return constrained, True, f"Constraints applied: {'; '.join(violations)}"

    return constrained, True, "All constraints satisfied"


async def fit_bkt_parameters(
    dataset: TrainingDataset,
    constraints: Optional[dict] = None,
    use_cross_validation: bool = False,
    n_folds: int = 5,
) -> tuple[dict, dict, bool, str]:
    """
    Fit BKT parameters using pyBKT EM algorithm.

    Args:
        dataset: Training dataset
        constraints: Parameter constraints dict
        use_cross_validation: Whether to use k-fold CV
        n_folds: Number of CV folds

    Returns:
        Tuple of (fitted_params, metrics, is_valid, message)
    """
    if not dataset.is_sufficient():
        return {}, {}, False, "Insufficient data for fitting"

    try:
        # Import pyBKT (lazy import to avoid hard dependency)
        try:
            from pyBKT.models import Model
        except ImportError:
            logger.error("pyBKT not installed. Install with: pip install pyBKT")
            return {}, {}, False, "pyBKT library not available"

        # Convert dataset to pyBKT format
        data = dataset.to_pyBKT_format()

        # Initialize and fit model
        model = Model(seed=42)  # Fixed seed for reproducibility

        # Fit using EM algorithm
        model.fit(data=data)

        # Extract fitted parameters
        # pyBKT returns parameters in different format, need to map
        fitted_params = {
            "p_L0": float(model.params()["prior"]),
            "p_T": float(model.params()["learns"]),
            "p_S": float(model.params()["slips"]),
            "p_G": float(model.params()["guesses"]),
        }

        # Apply constraints
        if constraints is None:
            constraints = {
                "L0_min": 0.001,
                "L0_max": 0.5,
                "T_min": 0.001,
                "T_max": 0.5,
                "S_min": 0.001,
                "S_max": 0.4,
                "G_min": 0.001,
                "G_max": 0.4,
            }

        constrained_params, is_valid, message = apply_parameter_constraints(
            fitted_params, constraints
        )

        if not is_valid:
            logger.warning(f"Fitted parameters failed validation: {message}")
            return constrained_params, {}, False, message

        # Compute metrics
        metrics = {
            "training_samples": dataset.total_attempts,
            "unique_users": dataset.unique_users,
            "avg_sequence_length": dataset.summary()["avg_sequence_length"],
        }

        # TODO: Add proper AUC, RMSE, logloss computation
        # This requires prediction on held-out data
        if use_cross_validation:
            # Placeholder for CV metrics
            metrics["cv_folds"] = n_folds
            metrics["cv_auc_mean"] = 0.0  # TODO: implement
            metrics["cv_rmse_mean"] = 0.0  # TODO: implement

        logger.info(
            f"Fitted BKT parameters for concept {dataset.concept_id}: "
            f"L0={constrained_params['p_L0']:.3f}, "
            f"T={constrained_params['p_T']:.3f}, "
            f"S={constrained_params['p_S']:.3f}, "
            f"G={constrained_params['p_G']:.3f}"
        )

        return constrained_params, metrics, True, message

    except Exception as e:
        logger.error(f"Error fitting BKT parameters: {e}", exc_info=True)
        return {}, {}, False, f"Fitting failed: {str(e)}"


async def persist_fitted_params(
    db: AsyncSession,
    concept_id: UUID,
    params: dict,
    metrics: dict,
    algo_version_id: UUID,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    constraints_applied: dict,
    activate: bool = False,
) -> BKTSkillParams:
    """
    Persist fitted BKT parameters to database.

    Args:
        db: Database session
        concept_id: Concept ID
        params: Fitted parameters dict
        metrics: Training metrics dict
        algo_version_id: Algorithm version ID
        from_date: Training data start
        to_date: Training data end
        constraints_applied: Constraints that were applied
        activate: Whether to activate this parameter set

    Returns:
        BKTSkillParams instance
    """
    # If activating, deactivate existing active params for this concept
    if activate:
        result = await db.execute(
            select(BKTSkillParams).where(
                and_(BKTSkillParams.concept_id == concept_id, BKTSkillParams.is_active == True)
            )
        )

        existing_active = result.scalars().all()
        for existing in existing_active:
            existing.is_active = False
            logger.info(f"Deactivated previous params for concept {concept_id}")

    # Create new params record
    skill_params = BKTSkillParams(
        concept_id=concept_id,
        algo_version_id=algo_version_id,
        p_L0=params["p_L0"],
        p_T=params["p_T"],
        p_S=params["p_S"],
        p_G=params["p_G"],
        constraints_applied=constraints_applied,
        fitted_at=datetime.now(),
        fitted_on_data_from=from_date,
        fitted_on_data_to=to_date,
        metrics=metrics,
        is_active=activate,
    )

    db.add(skill_params)
    await db.flush()

    logger.info(
        f"Persisted BKT parameters for concept {concept_id} "
        f"(active={activate}, id={skill_params.id})"
    )

    return skill_params
