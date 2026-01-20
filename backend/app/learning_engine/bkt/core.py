"""
BKT Core Math - Pure functions for Bayesian Knowledge Tracing.

Implements the standard 4-parameter BKT model:
- L0: Prior probability of mastery
- T: Probability of learning (transition)
- S: Probability of slip (learned but answers wrong)
- G: Probability of guess (unlearned but answers correct)

All functions include numerical stability guards to prevent NaN/Inf and
ensure probabilities remain in valid range [0, 1].
"""

import math
from typing import Tuple

from app.learning_engine.config import (
    BKT_L0_MIN,
    BKT_L0_MAX,
    BKT_T_MIN,
    BKT_T_MAX,
    BKT_S_MIN,
    BKT_S_MAX,
    BKT_G_MIN,
    BKT_G_MAX,
    BKT_STABILITY_EPSILON,
    BKT_MIN_PROB,
    BKT_MAX_PROB,
)


def clamp_probability(p: float) -> float:
    """
    Clamp a probability value to valid range [BKT_MIN_PROB, BKT_MAX_PROB].

    Args:
        p: Probability value

    Returns:
        Clamped probability in valid range
    """
    return max(BKT_MIN_PROB.value, min(BKT_MAX_PROB.value, p))


def predict_correct(p_L: float, p_S: float, p_G: float) -> float:
    """
    Predict probability of correct answer given current mastery state.

    Formula:
        P(Correct) = P(L) * (1 - P(S)) + (1 - P(L)) * P(G)

    This represents:
    - If learned (L), answer correctly with probability (1-S)
    - If not learned (~L), answer correctly with probability G

    Args:
        p_L: Current probability of mastery
        p_S: Probability of slip (learned but wrong)
        p_G: Probability of guess (unlearned but correct)

    Returns:
        Probability of correct answer
    """
    # Clamp inputs
    p_L = clamp_probability(p_L)
    p_S = clamp_probability(p_S)
    p_G = clamp_probability(p_G)

    # Calculate P(Correct)
    p_correct = p_L * (1.0 - p_S) + (1.0 - p_L) * p_G

    return clamp_probability(p_correct)


def posterior_given_obs(p_L: float, correct: bool, p_S: float, p_G: float) -> float:
    """
    Update mastery probability given an observation (Bayesian update).

    Formulas:
        P(L | Correct) = [P(L) * (1 - P(S))] / P(Correct)
        P(L | Wrong)   = [P(L) * P(S)] / P(Wrong)

    Where:
        P(Correct) = P(L) * (1 - P(S)) + (1 - P(L)) * P(G)
        P(Wrong) = 1 - P(Correct)

    Args:
        p_L: Prior probability of mastery
        correct: Whether the answer was correct
        p_S: Probability of slip
        p_G: Probability of guess

    Returns:
        Posterior probability of mastery given the observation
    """
    # Clamp inputs
    p_L = clamp_probability(p_L)
    p_S = clamp_probability(p_S)
    p_G = clamp_probability(p_G)

    # Calculate P(Correct)
    p_correct = predict_correct(p_L, p_S, p_G)

    if correct:
        # P(L | Correct) = [P(L) * (1 - P(S))] / P(Correct)
        numerator = p_L * (1.0 - p_S)
        denominator = p_correct
    else:
        # P(L | Wrong) = [P(L) * P(S)] / P(Wrong)
        numerator = p_L * p_S
        denominator = 1.0 - p_correct

    # Guard against division by zero
    if denominator < BKT_STABILITY_EPSILON.value:
        # If denominator is too small, return prior (no update)
        return p_L

    p_L_given_obs = numerator / denominator

    return clamp_probability(p_L_given_obs)


def apply_learning_transition(p_L_given_obs: float, p_T: float) -> float:
    """
    Apply learning transition to get next mastery state.

    Formula:
        P(L_next) = P(L | obs) + (1 - P(L | obs)) * P(T)

    This represents:
    - If already learned, stay learned
    - If not learned, learn with probability T

    Args:
        p_L_given_obs: Posterior probability after observation
        p_T: Probability of learning (transition)

    Returns:
        Updated probability of mastery after learning transition
    """
    # Clamp inputs
    p_L_given_obs = clamp_probability(p_L_given_obs)
    p_T = clamp_probability(p_T)

    # Apply transition
    p_L_next = p_L_given_obs + (1.0 - p_L_given_obs) * p_T

    return clamp_probability(p_L_next)


def update_mastery(
    p_L_current: float, correct: bool, p_T: float, p_S: float, p_G: float
) -> Tuple[float, dict]:
    """
    Complete BKT update: observation + learning transition.

    This is the main function that combines posterior update and learning transition.

    Steps:
    1. Update belief given observation (Bayesian update)
    2. Apply learning transition

    Args:
        p_L_current: Current mastery probability
        correct: Whether the answer was correct
        p_T: Probability of learning
        p_S: Probability of slip
        p_G: Probability of guess

    Returns:
        Tuple of (new_mastery, metadata_dict)
        - new_mastery: Updated mastery probability
        - metadata: Dict with intermediate values for debugging/logging
    """
    # Step 1: Predict probability of correct answer (for logging)
    p_correct_predicted = predict_correct(p_L_current, p_S, p_G)

    # Step 2: Update belief given observation
    p_L_given_obs = posterior_given_obs(p_L_current, correct, p_S, p_G)

    # Step 3: Apply learning transition
    p_L_next = apply_learning_transition(p_L_given_obs, p_T)

    # Metadata for debugging/logging
    metadata = {
        "p_L_prior": p_L_current,
        "p_correct_predicted": p_correct_predicted,
        "p_L_posterior": p_L_given_obs,
        "p_L_next": p_L_next,
        "observation": "correct" if correct else "wrong",
        "params_used": {
            "p_T": p_T,
            "p_S": p_S,
            "p_G": p_G,
        },
    }

    return p_L_next, metadata


def validate_bkt_params(p_L0: float, p_T: float, p_S: float, p_G: float) -> Tuple[bool, str]:
    """
    Validate BKT parameters for conceptual soundness.

    Checks:
    1. All parameters in (0, 1)
    2. P(Correct | Learned) > P(Correct | Unlearned)
       i.e., (1 - S) > G
    3. Slip and guess are not too high (< 0.5 by default)

    Args:
        p_L0: Prior mastery
        p_T: Learning rate
        p_S: Slip probability
        p_G: Guess probability

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check range using configured constraints
    if not (BKT_L0_MIN.value < p_L0 < BKT_L0_MAX.value):
        return False, f"L0 must be in ({BKT_L0_MIN.value}, {BKT_L0_MAX.value}), got {p_L0}"
    if not (BKT_T_MIN.value < p_T < BKT_T_MAX.value):
        return False, f"T must be in ({BKT_T_MIN.value}, {BKT_T_MAX.value}), got {p_T}"
    if not (BKT_S_MIN.value < p_S < BKT_S_MAX.value):
        return False, f"S must be in ({BKT_S_MIN.value}, {BKT_S_MAX.value}), got {p_S}"
    if not (BKT_G_MIN.value < p_G < BKT_G_MAX.value):
        return False, f"G must be in ({BKT_G_MIN.value}, {BKT_G_MAX.value}), got {p_G}"

    # Check conceptual constraint: learned should be better than unlearned
    p_correct_learned = 1.0 - p_S
    p_correct_unlearned = p_G

    if p_correct_learned <= p_correct_unlearned:
        return False, (
            f"Learned performance (1-S={p_correct_learned:.3f}) must be better than "
            f"unlearned performance (G={p_correct_unlearned:.3f})"
        )

    # Check slip and guess are reasonable (upper bounds from config)
    if p_S > BKT_S_MAX.value:
        return False, f"Slip probability too high: {p_S} > {BKT_S_MAX.value}"
    if p_G > BKT_G_MAX.value:
        return False, f"Guess probability too high: {p_G} > {BKT_G_MAX.value}"

    return True, ""


def check_degeneracy(
    p_L0: float, p_T: float, p_S: float, p_G: float, min_learning_gain: float = 0.05
) -> Tuple[bool, str]:
    """
    Check for BKT parameter degeneracy.

    Degeneracy occurs when:
    1. Learning rate T is too small (no learning happens)
    2. S and G are too close (learned vs unlearned indistinguishable)
    3. Expected mastery gain is too small

    Args:
        p_L0: Prior mastery
        p_T: Learning rate
        p_S: Slip probability
        p_G: Guess probability
        min_learning_gain: Minimum expected learning gain per correct answer

    Returns:
        Tuple of (is_non_degenerate, warning_message)
    """
    # Check if learning rate is too small (lower bound from config)
    if p_T < BKT_T_MIN.value:
        return False, f"Learning rate too small: T={p_T} < {BKT_T_MIN.value} (no learning)"

    # Check if slip and guess are too close
    performance_gap = (1.0 - p_S) - p_G
    if performance_gap < 0.1:
        return (
            False,
            f"Performance gap too small: (1-S)-G={performance_gap:.3f} < 0.1 (indistinguishable states)",
        )

    # Check expected learning gain on correct answer
    # Starting from p_L0, after one correct answer, what's the expected gain?
    p_L_after_correct, _ = update_mastery(p_L0, True, p_T, p_S, p_G)
    learning_gain = p_L_after_correct - p_L0

    if learning_gain < min_learning_gain:
        return False, f"Expected learning gain too small: {learning_gain:.3f} < {min_learning_gain}"

    return True, ""
