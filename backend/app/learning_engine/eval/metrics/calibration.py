"""Calibration metrics for probabilistic predictors."""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def log_loss(y_true: list[bool], y_pred: list[float], eps: float = 1e-15) -> float:
    """
    Compute binary cross-entropy (log loss).

    Args:
        y_true: Ground truth labels (0/1 or True/False)
        y_pred: Predicted probabilities [0, 1]
        eps: Small value to avoid log(0)

    Returns:
        Log loss (lower is better)
    """
    y_true = np.array([1 if x else 0 for x in y_true], dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    y_pred = np.clip(y_pred, eps, 1 - eps)

    return float(-np.mean(y_true * np.log(y_pred) + (1 - y_true) * np.log(1 - y_pred)))


def brier_score(y_true: list[bool], y_pred: list[float]) -> float:
    """
    Compute Brier score (mean squared error of probabilities).

    Args:
        y_true: Ground truth labels
        y_pred: Predicted probabilities [0, 1]

    Returns:
        Brier score (lower is better, range [0, 1])
    """
    y_true = np.array([1 if x else 0 for x in y_true], dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    return float(np.mean((y_true - y_pred) ** 2))


def expected_calibration_error(
    y_true: list[bool],
    y_pred: list[float],
    n_bins: int = 10,
) -> tuple[float, dict[str, Any]]:
    """
    Compute Expected Calibration Error (ECE) with fixed binning.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted probabilities [0, 1]
        n_bins: Number of bins

    Returns:
        Tuple of (ECE value, bin details)
    """
    y_true = np.array([1 if x else 0 for x in y_true], dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    # Bin predictions
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]

    ece = 0.0
    bin_details = []

    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        # Find predictions in this bin
        in_bin = (y_pred > bin_lower) & (y_pred <= bin_upper)
        prop_in_bin = in_bin.mean()

        if prop_in_bin > 0:
            # Accuracy in this bin
            accuracy_in_bin = y_true[in_bin].mean()
            # Average confidence in this bin
            avg_confidence_in_bin = y_pred[in_bin].mean()
            # Calibration error for this bin
            bin_ece = abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
            ece += bin_ece

            bin_details.append(
                {
                    "bin_lower": float(bin_lower),
                    "bin_upper": float(bin_upper),
                    "count": int(in_bin.sum()),
                    "mean_pred": float(avg_confidence_in_bin),
                    "mean_true": float(accuracy_in_bin),
                    "ece_contribution": float(bin_ece),
                }
            )
        else:
            bin_details.append(
                {
                    "bin_lower": float(bin_lower),
                    "bin_upper": float(bin_upper),
                    "count": 0,
                    "mean_pred": None,
                    "mean_true": None,
                    "ece_contribution": 0.0,
                }
            )

    return float(ece), {"bins": bin_details, "n_bins": n_bins}


def reliability_curve_data(
    y_true: list[bool],
    y_pred: list[float],
    n_bins: int = 10,
) -> dict[str, Any]:
    """
    Build reliability curve data for plotting.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted probabilities [0, 1]
        n_bins: Number of bins

    Returns:
        Dictionary with curve data points
    """
    ece, bin_details = expected_calibration_error(y_true, y_pred, n_bins)

    # Extract data for plotting
    bin_centers = []
    mean_preds = []
    mean_trues = []
    counts = []

    for bin_info in bin_details["bins"]:
        if bin_info["count"] > 0:
            bin_centers.append((bin_info["bin_lower"] + bin_info["bin_upper"]) / 2)
            mean_preds.append(bin_info["mean_pred"])
            mean_trues.append(bin_info["mean_true"])
            counts.append(bin_info["count"])

    return {
        "bin_centers": bin_centers,
        "mean_predicted": mean_preds,
        "mean_actual": mean_trues,
        "counts": counts,
        "ece": ece,
    }


def calibration_slope_intercept(
    y_true: list[bool],
    y_pred: list[float],
) -> dict[str, float | None]:
    """
    Compute calibration slope and intercept.

    Fits: logit(y_true) ~ logit(y_pred)

    Args:
        y_true: Ground truth labels
        y_pred: Predicted probabilities [0, 1]

    Returns:
        Dictionary with slope, intercept, and fit quality
    """
    from scipy import stats

    y_true = np.array([1 if x else 0 for x in y_true], dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    # Clip probabilities to avoid logit(0) or logit(1)
    eps = 1e-15
    y_pred = np.clip(y_pred, eps, 1 - eps)

    # Compute logits
    logit_pred = np.log(y_pred / (1 - y_pred))
    logit_true = np.log(y_true / (1 - y_true + eps))

    # Fit linear regression
    try:
        slope, intercept, r_value, p_value, std_err = stats.linregress(logit_pred, logit_true)
        return {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_value ** 2),
            "p_value": float(p_value),
            "std_err": float(std_err),
        }
    except Exception as e:
        logger.warning(f"Calibration slope/intercept fit failed: {e}")
        return {
            "slope": None,
            "intercept": None,
            "r_squared": None,
            "p_value": None,
            "std_err": None,
        }
