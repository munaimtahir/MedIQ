"""
Learning Engine Configuration - Central Constants Registry.

All constants used by learning algorithms MUST be defined here with proper provenance.
No magic numbers allowed in algorithm implementations.

Each constant includes:
- value: The actual constant value
- source: Citation (PDF, paper, library docs, etc.)
- notes: Rationale and context
- validated: Whether the value has been validated against source
"""

from dataclasses import dataclass, field
from typing import Any, List
import math


@dataclass(frozen=True)
class SourcedValue:
    """
    A constant value with documented provenance.

    All learning algorithm constants must use this type to enforce documentation.
    """

    value: Any
    source: str
    notes: str = ""
    validated: bool = False

    def __post_init__(self):
        if not self.source or self.source.strip() == "":
            raise ValueError(f"SourcedValue must have non-empty source. Got: {self.source}")


# =============================================================================
# FSRS (Spaced Repetition System) Constants
# =============================================================================

# FSRS-6 Default Weights
# Source: py-fsrs library v4.x default parameters
# Reference: https://github.com/open-spaced-repetition/py-fsrs
# These are the population-level defaults trained on large datasets
FSRS_DEFAULT_WEIGHTS = SourcedValue(
    value=[
        0.4072,
        1.1829,
        3.1262,
        15.4722,
        7.2102,
        0.5316,
        1.0651,
        0.0234,
        1.616,
        0.1544,
        1.0824,
        1.9813,
        0.0953,
        0.2975,
        2.2042,
        0.2407,
        2.9466,
        0.5034,
        0.6567,
    ],
    source="py-fsrs v4.x default parameters (https://github.com/open-spaced-repetition/py-fsrs)",
    notes="19 parameters for FSRS-6 algorithm. These are population-level defaults. "
    "Per-user tuning can improve performance but requires 300+ review logs.",
    validated=True,
)

# Desired Retention (Target Retrievability)
# Source: FSRS documentation and Anki default
# Reference: https://docs.ankiweb.net/deck-options.html#desired-retention
FSRS_DESIRED_RETENTION = SourcedValue(
    value=0.90,
    source="Anki/FSRS default desired retention (https://docs.ankiweb.net/deck-options.html)",
    notes="Target 90% retention probability. Can be adjusted per-user based on time constraints. "
    "Higher values = more reviews but better retention. Lower values = fewer reviews but more forgetting.",
    validated=True,
)

# Retention Bounds for Optimal Computation
FSRS_RETENTION_MIN = SourcedValue(
    value=0.70,
    source="FSRS heuristic: minimum practical retention target",
    notes="Below 70% retention, review efficiency decreases significantly.",
    validated=False,
)

FSRS_RETENTION_MAX = SourcedValue(
    value=0.95,
    source="FSRS heuristic: maximum practical retention target",
    notes="Above 95% retention, review burden increases exponentially with diminishing returns.",
    validated=False,
)

# Training Pipeline Thresholds
FSRS_MIN_LOGS_FOR_TRAINING = SourcedValue(
    value=300,
    source="FSRS recommendation for per-user optimization",
    notes="Minimum review logs required before attempting per-user weight fitting. "
    "Below this, use population defaults. This ensures sufficient data for reliable EM convergence.",
    validated=False,
)

FSRS_VALIDATION_SPLIT = SourcedValue(
    value=0.2,
    source="Standard ML practice: 80/20 train/val split",
    notes="Use last 20% of chronological data for validation to prevent overfitting.",
    validated=True,
)

FSRS_SHRINKAGE_MAX_ALPHA = SourcedValue(
    value=0.8,
    source="Regularization heuristic: limit user weight deviation",
    notes="Maximum weight to give user-specific weights vs population defaults. "
    "Prevents overfitting to small datasets. Alpha increases with log(n_samples).",
    validated=False,
)

FSRS_SHRINKAGE_TARGET_LOGS = SourcedValue(
    value=5000,
    source="FSRS recommendation: full personalization threshold",
    notes="Number of logs at which alpha reaches max (0.8). Formula: alpha = min(0.8, log(n)/log(5000))",
    validated=False,
)

# =============================================================================
# Rating Mapper Constants (MCQ Telemetry → FSRS Rating)
# =============================================================================

# Fast Answer Threshold
RATING_FAST_ANSWER_MS = SourcedValue(
    value=15000,  # 15 seconds
    source="Temporary heuristic - TO BE CALIBRATED from actual data",
    notes="Threshold for rating 4 (Easy). Answers faster than this with no changes → Easy. "
    "**CALIBRATION PLAN**: Compute p25 of time_per_question from first 1000 users, stratified by block.",
    validated=False,
)

# Slow Answer Threshold
RATING_SLOW_ANSWER_MS = SourcedValue(
    value=90000,  # 90 seconds
    source="Temporary heuristic - TO BE CALIBRATED from actual data",
    notes="Threshold for rating 2 (Hard). Answers slower than this → Hard. "
    "**CALIBRATION PLAN**: Compute p75 of time_per_question from first 1000 users, stratified by block.",
    validated=False,
)

# Max Changes for Confident Rating
RATING_MAX_CHANGES_FOR_CONFIDENT = SourcedValue(
    value=0,
    source="Conservative heuristic: any change indicates uncertainty",
    notes="Max answer changes to still be considered 'confident' (Easy). "
    "Current value (0) may be too strict. **CALIBRATION PLAN**: Analyze change_count distribution "
    "and correlate with eventual correctness.",
    validated=False,
)

# Telemetry Validation Bounds
TELEMETRY_MAX_TIME_MS = SourcedValue(
    value=3600000,  # 1 hour
    source="Sanity check: questions should not take > 1 hour",
    notes="Flag times above this as suspicious (possible user distractions).",
    validated=False,
)

TELEMETRY_MIN_TIME_MS = SourcedValue(
    value=500,  # 0.5 seconds
    source="Sanity check: minimum human response time",
    notes="Flag times below this as suspicious (possible cheating or timing errors).",
    validated=True,
)

TELEMETRY_MAX_CHANGES = SourcedValue(
    value=20,
    source="Sanity check: cap extreme change counts",
    notes="Cap change_count at this value to prevent outliers from skewing models.",
    validated=False,
)

# =============================================================================
# BKT (Bayesian Knowledge Tracing) Constants
# =============================================================================

# Numerical Stability
BKT_EPSILON = SourcedValue(
    value=1e-10,
    source="Standard numerical practice for probability computations",
    notes="Minimum probability value to avoid log(0) and division by zero. "
    "1e-10 chosen to balance precision (double has ~15 decimal digits) and stability.",
    validated=True,
)

BKT_MAX_PROB = SourcedValue(
    value=1.0 - 1e-10,
    source="Standard numerical practice for probability computations",
    notes="Maximum probability value. Ensures (1 - p) is never exactly zero.",
    validated=True,
)

# Default BKT Parameters (when no fitted params available)
# Source: pyBKT common defaults and BKT literature
# Reference: Baker, R.S.J.d., Corbett, A.T., Aleven, V. (2008). "More Accurate Student Modeling through Contextual Estimation of Slip and Guess Probabilities in Bayesian Knowledge Tracing"
BKT_DEFAULT_L0 = SourcedValue(
    value=0.1,
    source="pyBKT default + BKT literature (Baker et al. 2008)",
    notes="Prior probability of mastery: 10% is conservative starting point. "
    "Assumes students have some prior knowledge but are not yet proficient.",
    validated=True,
)

BKT_DEFAULT_T = SourcedValue(
    value=0.2,
    source="pyBKT default + BKT literature (Baker et al. 2008)",
    notes="Learning rate: 20% chance of learning per opportunity. "
    "Moderate learning rate suitable for medical exam concepts.",
    validated=True,
)

BKT_DEFAULT_S = SourcedValue(
    value=0.1,
    source="pyBKT default + BKT literature (Baker et al. 2008)",
    notes="Slip probability: 10% chance of error despite knowing concept. "
    "Low slip rate reflects that careless errors should be uncommon.",
    validated=True,
)

BKT_DEFAULT_G = SourcedValue(
    value=0.2,
    source="pyBKT default + BKT literature (Baker et al. 2008)",
    notes="Guess probability: 20% chance of correct answer without knowing. "
    "For 5-option MCQ, pure guessing would be 20%, so this is baseline.",
    validated=True,
)

# BKT Mastery Threshold
BKT_MASTERY_THRESHOLD = SourcedValue(
    value=0.95,
    source="Standard BKT practice: 95% mastery threshold",
    notes="Probability threshold for considering a concept 'mastered'. "
    "95% is stringent but appropriate for high-stakes medical exams.",
    validated=True,
)

# BKT Parameter Constraints
# Source: pyBKT guidance + degeneracy prevention
BKT_PARAM_MIN = SourcedValue(
    value=0.001,
    source="pyBKT constraint: parameters must be > 0",
    notes="Minimum value for all BKT parameters. Prevents degenerate cases (zero probabilities).",
    validated=True,
)

BKT_PARAM_MAX = SourcedValue(
    value=0.999,
    source="pyBKT constraint: parameters must be < 1",
    notes="Maximum value for all BKT parameters. Prevents degenerate cases (certainty).",
    validated=True,
)

# Slip/Guess Soft Constraints
# Source: BKT literature - typical values
BKT_SLIP_SOFT_MAX = SourcedValue(
    value=0.3,
    source="BKT literature: slip typically < 30%",
    notes="Soft constraint (warning, not rejection). Slip > 30% suggests either very hard questions "
    "or model misspecification. **NOT ENFORCED** - used for flagging only.",
    validated=True,
)

BKT_GUESS_SOFT_MAX = SourcedValue(
    value=0.3,
    source="BKT literature: guess typically < 30%",
    notes="Soft constraint (warning, not rejection). Guess > 30% suggests questions might be too easy "
    "or have obvious distractors. **NOT ENFORCED** - used for flagging only.",
    validated=True,
)

# Degeneracy Check: (1 - S) > G
# Source: BKT theory - must be able to distinguish learned from unlearned
BKT_DEGENERACY_MIN_GAP = SourcedValue(
    value=0.05,
    source="BKT degeneracy prevention: P(Correct|Learned) must exceed P(Correct|Unlearned)",
    notes="Minimum gap between (1-S) and G. If (1-S) - G < 0.05, model cannot reliably distinguish states. "
    "**ENFORCED**: Fits violating this are rejected.",
    validated=True,
)

# Training Thresholds
BKT_MIN_ATTEMPTS_PER_CONCEPT = SourcedValue(
    value=10,
    source="Statistical reliability: minimum sample size for parameter estimation",
    notes="Minimum total attempts on a concept before attempting to fit BKT parameters. "
    "Below this, use defaults.",
    validated=False,
)

BKT_MIN_USERS_PER_CONCEPT = SourcedValue(
    value=3,
    source="Statistical reliability: minimum users for generalization",
    notes="Minimum unique users with attempts on a concept. Prevents overfitting to single user's pattern.",
    validated=False,
)

# =============================================================================
# Mastery v0 Constants (Simple Theme-Level Mastery)
# =============================================================================

# Difficulty Weights
MASTERY_DIFFICULTY_WEIGHT_EASY = SourcedValue(
    value=0.90,
    source="Temporary heuristic - TO BE CALIBRATED from actual data",
    notes="Weight for easy questions in mastery calculation. "
    "**CALIBRATION PLAN**: Fit from actual pass rates stratified by difficulty.",
    validated=False,
)

MASTERY_DIFFICULTY_WEIGHT_MEDIUM = SourcedValue(
    value=1.00,
    source="Baseline weight (no adjustment)",
    notes="Medium difficulty questions have neutral weight (1.0).",
    validated=True,
)

MASTERY_DIFFICULTY_WEIGHT_HARD = SourcedValue(
    value=1.10,
    source="Temporary heuristic - TO BE CALIBRATED from actual data",
    notes="Weight for hard questions in mastery calculation. "
    "**CALIBRATION PLAN**: Fit from actual pass rates stratified by difficulty.",
    validated=False,
)

# Mastery v0 Parameters
MASTERY_LOOKBACK_DAYS = SourcedValue(
    value=90,
    source="Spaced repetition literature: ~3 months is meaningful memory window",
    notes="Consider attempts from last 90 days for mastery calculation. "
    "Older attempts may not reflect current knowledge state.",
    validated=True,
)

MASTERY_MIN_ATTEMPTS = SourcedValue(
    value=3,
    source="Statistical reliability: minimum observations",
    notes="Minimum attempts on a theme before computing mastery score.",
    validated=False,
)

MASTERY_RECENCY_BUCKETS = SourcedValue(
    value=[0, 7, 30, 90],  # days
    source="Spaced repetition intervals: recent, last week, last month, last 3 months",
    notes="Time buckets for recency weighting. More recent attempts weighted higher.",
    validated=False,
)

# =============================================================================
# Validation Functions
# =============================================================================


def validate_all_constants():
    """
    Validate all constants at import time.

    Raises:
        ValueError: If any constant fails validation
    """
    errors = []

    # FSRS weights must be 19 parameters
    if len(FSRS_DEFAULT_WEIGHTS.value) != 19:
        errors.append(
            f"FSRS weights must have 19 parameters, got {len(FSRS_DEFAULT_WEIGHTS.value)}"
        )

    # All FSRS weights must be finite
    for i, w in enumerate(FSRS_DEFAULT_WEIGHTS.value):
        if not math.isfinite(w):
            errors.append(f"FSRS weight {i} is not finite: {w}")

    # Retention values must be in (0, 1)
    for name, const in [
        ("FSRS_DESIRED_RETENTION", FSRS_DESIRED_RETENTION),
        ("FSRS_RETENTION_MIN", FSRS_RETENTION_MIN),
        ("FSRS_RETENTION_MAX", FSRS_RETENTION_MAX),
    ]:
        if not (0 < const.value < 1):
            errors.append(f"{name} must be in (0, 1), got {const.value}")

    # BKT thresholds must be in (0, 1)
    if not (0 < BKT_MASTERY_THRESHOLD.value < 1):
        errors.append(f"BKT_MASTERY_THRESHOLD must be in (0, 1), got {BKT_MASTERY_THRESHOLD.value}")

    # BKT defaults must satisfy basic constraints
    if not (BKT_DEFAULT_S.value + BKT_DEFAULT_G.value < 1.0):
        errors.append(f"BKT: S + G must be < 1, got {BKT_DEFAULT_S.value} + {BKT_DEFAULT_G.value}")

    if not ((1.0 - BKT_DEFAULT_S.value) > BKT_DEFAULT_G.value):
        errors.append(f"BKT: (1-S) must be > G for distinguishability")

    # Timings must be positive
    if RATING_FAST_ANSWER_MS.value <= 0:
        errors.append("RATING_FAST_ANSWER_MS must be positive")
    if RATING_SLOW_ANSWER_MS.value <= 0:
        errors.append("RATING_SLOW_ANSWER_MS must be positive")
    if RATING_FAST_ANSWER_MS.value >= RATING_SLOW_ANSWER_MS.value:
        errors.append("RATING_FAST_ANSWER_MS must be < RATING_SLOW_ANSWER_MS")

    if errors:
        raise ValueError(f"Constant validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# Validate on import
validate_all_constants()


# === 7. Difficulty Calibration (Elo v1) Constants ===

# Probability Model Parameters
ELO_GUESS_FLOOR = SourcedValue(
    value=0.20,
    sources=[
        "5-option MCQ: random guessing yields 1/5 = 0.20 probability",
        "Standard multiple-choice testing theory: P(guess) = 1 / number_of_options",
    ],
)

ELO_SCALE = SourcedValue(
    value=400.0,
    sources=[
        "Standard Elo scaling factor: 400 points ≈ 10x performance difference",
        "Derived from chess Elo where 400-point difference implies ~91% expected score",
        "Equivalent to logistic scale: 400 / ln(10) ≈ 173.7 (but 400 is conventional)",
    ],
)

# Base K Values (before uncertainty modulation)
ELO_K_BASE_USER = SourcedValue(
    value=32.0,
    sources=[
        "Standard Elo K-factor for active players (FIDE uses 10-40 range)",
        "Higher than chess default (16) due to MCQ noise and learning effects",
        "Placeholder - to be tuned via cross-validation on historical data",
    ],
)

ELO_K_BASE_QUESTION = SourcedValue(
    value=24.0,
    sources=[
        "Slightly lower than user K to prioritize user ability adaptation",
        "Questions are more stable than users (no learning curve for items)",
        "Placeholder - to be tuned from data; initial heuristic is 75% of user K",
    ],
)

ELO_K_MIN = SourcedValue(
    value=8.0,
    sources=[
        "Minimum K for mature ratings with low uncertainty",
        "Prevents complete stagnation while maintaining stability",
        "Heuristic: 25% of base K for well-established ratings",
    ],
)

ELO_K_MAX = SourcedValue(
    value=64.0,
    sources=[
        "Maximum K for new items with high uncertainty",
        "Enables fast adaptation in early stages",
        "Heuristic: 2x base K for maximum learning rate",
    ],
)

# Uncertainty Dynamics
ELO_UNC_INIT_USER = SourcedValue(
    value=350.0,
    sources=[
        "Initial rating deviation for new users",
        "Similar to Glicko-2 RD_0 = 350 (standard for online rating systems)",
        "Represents ~87% confidence interval of ±1.4 * 350 ≈ ±490 rating points",
    ],
)

ELO_UNC_INIT_QUESTION = SourcedValue(
    value=250.0,
    sources=[
        "Lower initial uncertainty for questions (assumed more stable than users)",
        "Heuristic: ~70% of user initial uncertainty",
        "Questions don't learn, so uncertainty primarily reflects estimation noise",
    ],
)

ELO_UNC_FLOOR = SourcedValue(
    value=50.0,
    sources=[
        "Minimum uncertainty floor (never fully certain)",
        "Represents irreducible measurement noise in MCQ performance",
        "Glicko-2 typically converges to RD ≈ 30-50 for active players",
    ],
)

ELO_UNC_DECAY_PER_ATTEMPT = SourcedValue(
    value=0.9,
    sources=[
        "Uncertainty multiplier per attempt: unc *= 0.9 each time",
        "Geometric decay toward floor: after 20 attempts, unc ≈ 0.9^20 ≈ 0.12 of initial",
        "Heuristic - to be calibrated from variance of rating changes over time",
    ],
)

ELO_UNC_AGE_INCREASE_PER_DAY = SourcedValue(
    value=1.0,
    sources=[
        "Uncertainty increase per day of inactivity",
        "Models drift and forgetting (user ability may change; question difficulty may shift due to curriculum changes)",
        "Heuristic: ~1 point/day; 90 days inactivity adds ~90 points RD (modest drift)",
    ],
)

# Theme Rating Activation Thresholds
ELO_MIN_ATTEMPTS_THEME_USER = SourcedValue(
    value=5,
    sources=[
        "Minimum attempts in a theme before creating theme-specific user rating",
        "Heuristic: Require some exposure before splitting from global rating",
        "Prevents noisy theme ratings with insufficient data",
    ],
)

ELO_MIN_ATTEMPTS_THEME_QUESTION = SourcedValue(
    value=3,
    sources=[
        "Minimum attempts on a question in a theme before theme-specific difficulty",
        "Lower than user threshold (questions more stable)",
        "Heuristic - to be validated with hierarchical model evaluation",
    ],
)

ELO_THEME_UPDATE_WEIGHT = SourcedValue(
    value=0.5,
    sources=[
        "Weight for theme rating update relative to global",
        "0.5 = equal update to both global and theme ratings",
        "Hierarchical model: total update split between levels",
        "Placeholder - to be tuned via nested cross-validation",
    ],
)

# Drift Control (Recenter)
ELO_RECENTER_ENABLED = SourcedValue(
    value=True,
    sources=[
        "Enable periodic recentering to prevent rating inflation/deflation",
        "Standard practice in Elo systems (FIDE periodically adjusts baselines)",
        "Preserves relative differences while normalizing absolute scale",
    ],
)

ELO_RECENTER_EVERY_N_UPDATES = SourcedValue(
    value=10000,
    sources=[
        "Recenter after every 10,000 updates (global)",
        "Heuristic: Frequent enough to prevent drift, infrequent enough to avoid instability",
        "Typical platform with 1,000 students × 50 questions/month ⇒ recenter ~monthly",
    ],
)

ELO_RATING_INIT = SourcedValue(
    value=0.0,
    sources=[
        "Initial rating for new users and questions (mean-centered)",
        "Elo convention: start at system average (often 1500 in chess, but 0 for normalized scale)",
        "0-centered scale simplifies interpretation: positive = above average, negative = below average",
    ],
)


# =============================================================================
# Convenience Accessors
# =============================================================================


def get_fsrs_defaults() -> dict:
    """Get FSRS defaults as a dict."""
    return {
        "weights": FSRS_DEFAULT_WEIGHTS.value,
        "desired_retention": FSRS_DESIRED_RETENTION.value,
    }


def get_bkt_defaults() -> dict:
    """Get BKT defaults as a dict."""
    return {
        "p_L0": BKT_DEFAULT_L0.value,
        "p_T": BKT_DEFAULT_T.value,
        "p_S": BKT_DEFAULT_S.value,
        "p_G": BKT_DEFAULT_G.value,
    }


def get_rating_thresholds() -> dict:
    """Get rating mapper thresholds as a dict."""
    return {
        "fast_answer_ms": RATING_FAST_ANSWER_MS.value,
        "slow_answer_ms": RATING_SLOW_ANSWER_MS.value,
        "max_changes_for_confident": RATING_MAX_CHANGES_FOR_CONFIDENT.value,
    }


def get_elo_defaults() -> dict:
    """Get Elo difficulty calibration defaults as a dict."""
    return {
        "guess_floor": ELO_GUESS_FLOOR.value,
        "scale": ELO_SCALE.value,
        "k_base_user": ELO_K_BASE_USER.value,
        "k_base_question": ELO_K_BASE_QUESTION.value,
        "k_min": ELO_K_MIN.value,
        "k_max": ELO_K_MAX.value,
        "unc_init_user": ELO_UNC_INIT_USER.value,
        "unc_init_question": ELO_UNC_INIT_QUESTION.value,
        "unc_floor": ELO_UNC_FLOOR.value,
        "unc_decay_per_attempt": ELO_UNC_DECAY_PER_ATTEMPT.value,
        "unc_age_increase_per_day": ELO_UNC_AGE_INCREASE_PER_DAY.value,
        "min_attempts_theme_user": ELO_MIN_ATTEMPTS_THEME_USER.value,
        "min_attempts_theme_question": ELO_MIN_ATTEMPTS_THEME_QUESTION.value,
        "theme_update_weight": ELO_THEME_UPDATE_WEIGHT.value,
        "recenter_enabled": ELO_RECENTER_ENABLED.value,
        "recenter_every_n_updates": ELO_RECENTER_EVERY_N_UPDATES.value,
        "rating_init": ELO_RATING_INIT.value,
    }
