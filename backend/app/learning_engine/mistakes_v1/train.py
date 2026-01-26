"""Offline training pipeline for Mistake Engine v1."""

import logging
import subprocess
from collections import Counter
from datetime import date, datetime
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import lightgbm as lgb
except ImportError:
    lgb = None
    logging.warning("LightGBM not available. Install with: pip install lightgbm")

from app.learning_engine.constants import AlgoKey
from app.learning_engine.mistakes_v1.features import extract_features_v1_for_session, features_to_dict
from app.learning_engine.mistakes_v1.registry import (
    create_model_version,
    get_model_version_by_id,
    save_model_artifact,
)
from app.learning_engine.mistakes_v1.schemas import (
    CalibrationType,
    ModelType,
    TrainingConfig,
    TrainingMetrics,
)
from app.learning_engine.mistakes_v1.weak_labels import generate_weak_labels_batch
from app.learning_engine.registry import resolve_active
from app.models.mistakes import MistakeTrainingRun
from app.models.session import SessionAnswer, TestSession

logger = logging.getLogger(__name__)


def get_git_commit() -> str | None:
    """
    Get current git commit hash.

    Returns:
        Git commit hash or None if not available
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


async def build_training_dataset(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> tuple[list[Any], list[str], list[float]]:
    """
    Build training dataset from Postgres.

    Joins attempts + telemetry + question metadata + user stats.

    Args:
        db: Database session
        start_date: Training window start
        end_date: Training window end

    Returns:
        Tuple of (features_list, labels, confidences)
    """
    logger.info(f"Building dataset from {start_date} to {end_date}")

    # Get all sessions in date range
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    stmt = (
        select(TestSession)
        .where(
            TestSession.submitted_at >= start_datetime,
            TestSession.submitted_at <= end_datetime,
        )
        .order_by(TestSession.submitted_at)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    logger.info(f"Found {len(sessions)} sessions in date range")

    # Extract features for all sessions
    all_features = []

    for session in sessions:
        try:
            features_list = await extract_features_v1_for_session(db, session.id)
            all_features.extend(features_list)
        except Exception as e:
            logger.warning(f"Failed to extract features for session {session.id}: {e}")
            continue

    logger.info(f"Extracted features for {len(all_features)} attempts")

    # Generate weak labels
    version, params_obj = await resolve_active(db, AlgoKey.MISTAKES.value)
    if not version or not params_obj:
        logger.warning("No active v0 algorithm found, using default params")
        params = {}
    else:
        params = params_obj.params_json

    labeled_data = generate_weak_labels_batch(all_features, params)

    # Extract labels and confidences
    all_labels = []
    all_confidences = []
    labeled_features = []

    for features, weak_label in labeled_data:
        labeled_features.append(features)
        all_labels.append(weak_label.mistake_type)
        all_confidences.append(weak_label.confidence)

    # Use only labeled features (wrong answers only)
    all_features = labeled_features

    logger.info(f"Generated {len(all_labels)} weak labels")

    return all_features, all_labels, all_confidences


def prepare_feature_matrix(
    features_list: list[Any],
    metadata: dict[str, Any] | None = None,
) -> tuple[np.ndarray, list[str]]:
    """
    Convert features list to feature matrix.

    Args:
        features_list: List of AttemptFeaturesV1
        metadata: Optional metadata (for feature order)

    Returns:
        Tuple of (feature_matrix, feature_names)
    """
    if not features_list:
        return np.array([]), []

    # Convert to dicts
    feature_dicts = [features_to_dict(f) for f in features_list]

    # Get feature order
    if metadata and "feature_order" in metadata:
        feature_order = metadata["feature_order"]
    else:
        # Use first dict's keys as order
        feature_order = sorted(feature_dicts[0].keys())

    # Build matrix
    matrix = np.array([[d.get(f, 0.0) for f in feature_order] for d in feature_dicts])

    return matrix, feature_order


def train_logistic_regression(
    X_train: np.ndarray,
    y_train: list[str],
    sample_weights: np.ndarray | None = None,
    hyperparams: dict[str, Any] | None = None,
) -> tuple[LogisticRegression, dict[str, Any]]:
    """
    Train multinomial logistic regression baseline.

    Args:
        X_train: Training features
        y_train: Training labels
        sample_weights: Sample weights (from label confidence)
        hyperparams: Hyperparameters

    Returns:
        Tuple of (trained_model, metadata)
    """
    hyperparams = hyperparams or {}
    model = LogisticRegression(
        multi_class="multinomial",
        solver="lbfgs",
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
        **hyperparams,
    )

    model.fit(X_train, y_train, sample_weight=sample_weights)

    metadata = {
        "model_type": "LOGREG",
        "classes": list(model.classes_),
        "n_features": X_train.shape[1],
        "n_samples": X_train.shape[0],
    }

    return model, metadata


def train_lightgbm(
    X_train: np.ndarray,
    y_train: list[str],
    X_val: np.ndarray,
    y_val: list[str],
    sample_weights: np.ndarray | None = None,
    hyperparams: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, Any]]:
    """
    Train LightGBM multiclass classifier.

    Uses sklearn wrapper for compatibility with calibration.

    Args:
        X_train: Training features
        y_train: Training labels
        X_val: Validation features
        y_val: Validation labels
        sample_weights: Sample weights
        hyperparams: Hyperparameters

    Returns:
        Tuple of (trained_model, metadata)
    """
    if lgb is None:
        raise ImportError("LightGBM not installed. Install with: pip install lightgbm")

    hyperparams = hyperparams or {}
    default_params = {
        "objective": "multiclass",
        "num_class": len(set(y_train)),
        "metric": "multi_logloss",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "random_state": 42,
    }
    default_params.update(hyperparams)

    # Use sklearn wrapper for compatibility
    from sklearn.preprocessing import LabelEncoder

    le = LabelEncoder()
    y_train_encoded = le.fit_transform(y_train)
    y_val_encoded = le.transform(y_val)

    model = lgb.LGBMClassifier(
        n_estimators=100,
        num_leaves=default_params.get("num_leaves", 31),
        learning_rate=default_params.get("learning_rate", 0.05),
        feature_fraction=default_params.get("feature_fraction", 0.9),
        bagging_fraction=default_params.get("bagging_fraction", 0.8),
        bagging_freq=default_params.get("bagging_freq", 5),
        verbose=-1,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(
        X_train,
        y_train_encoded,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val_encoded)],
        callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(period=0)],
    )

    # Store label encoder in model for prediction
    model._label_encoder = le

    metadata = {
        "model_type": "LGBM",
        "classes": list(le.classes_),
        "n_features": X_train.shape[1],
        "n_samples": X_train.shape[0],
    }

    return model, metadata


def calibrate_model(
    model: Any,
    X_val: np.ndarray,
    y_val: list[str],
    calibration_type: CalibrationType = CalibrationType.ISOTONIC,
) -> tuple[Any, dict[str, Any]]:
    """
    Calibrate model probabilities.

    Args:
        model: Trained model
        X_val: Validation features
        y_val: Validation labels
        calibration_type: Calibration method

    Returns:
        Tuple of (calibrated_model, metadata)
    """
    if calibration_type == CalibrationType.NONE:
        return model, {"calibration_type": "NONE"}

    # Wrap model in CalibratedClassifierCV
    method = "isotonic" if calibration_type == CalibrationType.ISOTONIC else "sigmoid"
    calibrated = CalibratedClassifierCV(model, method=method, cv="prefit")
    calibrated.fit(X_val, y_val)

    return calibrated, {"calibration_type": calibration_type.value, "method": method}


def compute_metrics(
    model: Any,
    X_val: np.ndarray,
    y_val: list[str],
    classes: list[str],
) -> TrainingMetrics:
    """
    Compute training metrics.

    Args:
        model: Trained model
        X_val: Validation features
        y_val: Validation labels
        classes: Class names

    Returns:
        TrainingMetrics
    """
    # Predictions
    y_pred = model.predict(X_val)

    # F1 scores
    macro_f1 = f1_score(y_val, y_pred, average="macro")
    weighted_f1 = f1_score(y_val, y_pred, average="weighted")

    # Confusion matrix
    cm = confusion_matrix(y_val, y_pred, labels=classes)
    cm_list = cm.tolist()

    # Class distribution
    class_dist = Counter(y_val)

    # Calibration error (simplified - would need proper ECE computation)
    calibration_ece = None
    try:
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_val)
            # TODO: Compute proper ECE (Expected Calibration Error)
            # For now, leave as None
    except Exception:
        pass

    return TrainingMetrics(
        macro_f1=float(macro_f1),
        weighted_f1=float(weighted_f1),
        calibration_ece=calibration_ece,
        confusion_matrix=cm_list,
        class_distribution=dict(class_dist),
        train_samples=0,  # Will be set by caller
        val_samples=len(y_val),
    )


async def train_model(
    db: AsyncSession,
    config: TrainingConfig,
    run_by_user_id: UUID | None = None,
) -> tuple[UUID, TrainingMetrics]:
    """
    Train a new model version.

    Args:
        db: Database session
        config: Training configuration
        run_by_user_id: User ID who triggered training

    Returns:
        Tuple of (model_version_id, metrics)
    """
    logger.info(f"Starting training: {config.model_type.value} from {config.start_date} to {config.end_date}")

    # Create training run
    training_run = MistakeTrainingRun(
        started_at=datetime.utcnow(),
        success=False,
        run_by=run_by_user_id,
        git_commit=get_git_commit(),
        hyperparams_json=config.hyperparams,
    )
    db.add(training_run)
    await db.flush()

    try:
        # Build dataset
        features_list, labels, confidences = await build_training_dataset(
            db, config.start_date, config.end_date
        )

        if len(features_list) < 100:
            raise ValueError(f"Insufficient data: only {len(features_list)} samples")

        training_run.data_row_count = len(features_list)
        training_run.class_distribution_json = dict(Counter(labels))

        # Prepare feature matrix
        X, feature_order = prepare_feature_matrix(features_list)
        y = np.array(labels)
        sample_weights = np.array(confidences)

        # Train/val split (time-based to avoid leakage)
        # Use last 20% for validation
        split_idx = int(len(X) * config.train_split)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        weights_train, weights_val = sample_weights[:split_idx], sample_weights[split_idx:]

        logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}")

        # Train model
        if config.model_type == ModelType.LOGREG:
            model, model_metadata = train_logistic_regression(
                X_train, y_train, weights_train, config.hyperparams
            )
        elif config.model_type == ModelType.LGBM:
            model, model_metadata = train_lightgbm(
                X_train, y_train, X_val, y_val, weights_train, config.hyperparams
            )
        else:
            raise ValueError(f"Unknown model type: {config.model_type}")

        # Calibrate
        if config.calibration_type != CalibrationType.NONE:
            model, cal_metadata = calibrate_model(model, X_val, y_val, config.calibration_type)
            model_metadata.update(cal_metadata)

        # Compute metrics
        metrics = compute_metrics(model, X_val, y_val, model_metadata["classes"])
        metrics.train_samples = len(X_train)

        # Save model artifact
        model_metadata["feature_order"] = feature_order
        artifact_path = save_model_artifact(
            training_run.id,  # Use training_run.id as temporary ID
            model,
            model_metadata,
        )

        # Create model version
        model_version = await create_model_version(
            db,
            config.model_type,
            config.feature_schema_version,
            config.label_schema_version,
            config.start_date,
            config.end_date,
            metrics.model_dump(),
            artifact_path,
            config.calibration_type,
            config.notes,
        )

        # Update artifact path with model_version_id
        final_artifact_path = save_model_artifact(model_version.id, model, model_metadata)
        model_version.artifact_path = final_artifact_path
        await db.commit()

        # Update training run
        training_run.model_version_id = model_version.id
        training_run.finished_at = datetime.utcnow()
        training_run.success = True
        await db.commit()

        logger.info(f"Training completed: model_version_id={model_version.id}")

        return model_version.id, metrics

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        training_run.finished_at = datetime.utcnow()
        training_run.success = False
        training_run.error_text = str(e)
        await db.commit()
        raise
