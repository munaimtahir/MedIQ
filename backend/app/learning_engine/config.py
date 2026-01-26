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

import math
from dataclasses import dataclass
from typing import Any


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
        errors.append("BKT: (1-S) must be > G for distinguishability")

    # Timings must be positive
    if RATING_FAST_ANSWER_MS.value <= 0:
        errors.append("RATING_FAST_ANSWER_MS must be positive")
    if RATING_SLOW_ANSWER_MS.value <= 0:
        errors.append("RATING_SLOW_ANSWER_MS must be positive")
    if RATING_FAST_ANSWER_MS.value >= RATING_SLOW_ANSWER_MS.value:
        errors.append("RATING_FAST_ANSWER_MS must be < RATING_SLOW_ANSWER_MS")

    if errors:
        raise ValueError("Constant validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# Validate on import
validate_all_constants()


# === 7. Difficulty Calibration (Elo v1) Constants ===

# Probability Model Parameters
ELO_GUESS_FLOOR = SourcedValue(
    value=0.20,
    source="5-option MCQ: random guessing yields 1/5 = 0.20 probability; Standard multiple-choice testing theory: P(guess) = 1 / number_of_options",
)

ELO_SCALE = SourcedValue(
    value=400.0,
    source="Standard Elo scaling factor: 400 points ≈ 10x performance difference; Derived from chess Elo where 400-point difference implies ~91% expected score",
)

# Base K Values (before uncertainty modulation)
ELO_K_BASE_USER = SourcedValue(
    value=32.0,
    source="Standard Elo K-factor for active players (FIDE uses 10-40 range); Higher than chess default (16) due to MCQ noise and learning effects",
)

ELO_K_BASE_QUESTION = SourcedValue(
    value=24.0,
    source="Slightly lower than user K to prioritize user ability adaptation; Questions are more stable than users (no learning curve for items)",
)

ELO_K_MIN = SourcedValue(
    value=8.0,
    source="Minimum K for mature ratings with low uncertainty; Prevents complete stagnation while maintaining stability",
)

ELO_K_MAX = SourcedValue(
    value=64.0,
    source="Maximum K for new items with high uncertainty; Enables fast adaptation in early stages",
)

# Uncertainty Dynamics
ELO_UNC_INIT_USER = SourcedValue(
    value=350.0,
    source="Initial rating deviation for new users; Similar to Glicko-2 RD_0 = 350 (standard for online rating systems)",
)

ELO_UNC_INIT_QUESTION = SourcedValue(
    value=250.0,
    source="Lower initial uncertainty for questions (assumed more stable than users); Heuristic: ~70% of user initial uncertainty",
)

ELO_UNC_FLOOR = SourcedValue(
    value=50.0,
    source="Minimum uncertainty floor (never fully certain); Represents irreducible measurement noise in MCQ performance",
)

ELO_UNC_DECAY_PER_ATTEMPT = SourcedValue(
    value=0.9,
    source="Uncertainty multiplier per attempt: unc *= 0.9 each time; Geometric decay toward floor",
)

ELO_UNC_AGE_INCREASE_PER_DAY = SourcedValue(
    value=1.0,
    source="Uncertainty increase per day of inactivity; Models drift and forgetting",
)

# Theme Rating Activation Thresholds
ELO_MIN_ATTEMPTS_THEME_USER = SourcedValue(
    value=5,
    source="Minimum attempts in a theme before creating theme-specific user rating; Prevents noisy theme ratings with insufficient data",
)

ELO_MIN_ATTEMPTS_THEME_QUESTION = SourcedValue(
    value=3,
    source="Minimum attempts on a question in a theme before theme-specific difficulty; Lower than user threshold (questions more stable)",
)

ELO_THEME_UPDATE_WEIGHT = SourcedValue(
    value=0.5,
    source="Weight for theme rating update relative to global; 0.5 = equal update to both global and theme ratings",
)

# Drift Control (Recenter)
ELO_RECENTER_ENABLED = SourcedValue(
    value=True,
    source="Enable periodic recentering to prevent rating inflation/deflation; Standard practice in Elo systems",
)

ELO_RECENTER_EVERY_N_UPDATES = SourcedValue(
    value=10000,
    source="Recenter after every 10,000 updates (global); Heuristic: Frequent enough to prevent drift, infrequent enough to avoid instability",
)

ELO_RATING_INIT = SourcedValue(
    value=0.0,
    source="Initial rating for new users and questions (mean-centered); 0-centered scale simplifies interpretation",
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


# =============================================================================
# Adaptive Selection v1 (Constrained Thompson Sampling Bandit) Constants
# =============================================================================

# Beta Prior Parameters (Uniform prior = maximum uncertainty)
ADAPTIVE_BETA_PRIOR_A = SourcedValue(
    value=1.0,
    source="Beta(1,1) = Uniform distribution (uninformative prior)",
    notes="Starting with no preference allows learning from data. "
    "Could use Beta(2,2) for slightly conservative prior centered at 0.5.",
    validated=True,
)

ADAPTIVE_BETA_PRIOR_B = SourcedValue(
    value=1.0,
    source="Beta(1,1) = Uniform distribution (uninformative prior)",
    notes="Symmetric with alpha for balanced initial exploration.",
    validated=True,
)

# Epsilon Floor (prevents zeroing low-history arms)
ADAPTIVE_EPSILON_FLOOR = SourcedValue(
    value=0.10,
    source="Epsilon-greedy hybrid: minimum exploration rate",
    notes="Ensures themes with low history still get some chance. "
    "final_score = base_priority * (epsilon + sampled_y). "
    "10% floor prevents complete neglect of any theme.",
    validated=False,
)

# Theme Selection Constraints
ADAPTIVE_MAX_CANDIDATE_THEMES = SourcedValue(
    value=30,
    source="Performance constraint: limit candidate set size",
    notes="Prevents excessive computation for users with many themes. "
    "Most medical syllabi have 20-50 themes per block.",
    validated=False,
)

ADAPTIVE_MIN_THEME_COUNT = SourcedValue(
    value=2,
    source="Curriculum coverage: minimum theme diversity per session",
    notes="Ensures sessions cover at least 2 themes for variety. "
    "Can be relaxed if total questions < 10.",
    validated=False,
)

ADAPTIVE_MAX_THEME_COUNT = SourcedValue(
    value=5,
    source="Focus constraint: maximum themes per session",
    notes="Too many themes reduces depth. 5 themes for ~20 questions = ~4 per theme minimum.",
    validated=False,
)

ADAPTIVE_MIN_PER_THEME = SourcedValue(
    value=3,
    source="Statistical reliability: minimum questions per theme",
    notes="Ensures meaningful exposure to each selected theme. "
    "Below 3 questions, learning signal is too weak.",
    validated=False,
)

ADAPTIVE_MAX_PER_THEME = SourcedValue(
    value=20,
    source="Balance constraint: maximum questions per theme",
    notes="Prevents over-concentration on single theme. "
    "Typical session of 20-30 questions should span multiple themes.",
    validated=False,
)

# Repeat Exclusion (Anti-repeat policy)
ADAPTIVE_EXCLUDE_SEEN_WITHIN_DAYS = SourcedValue(
    value=14,
    source="Spaced repetition principle: minimum interval before repeat",
    notes="Questions seen in last 14 days are excluded unless supply is low. "
    "Prevents cramming same questions repeatedly.",
    validated=False,
)

ADAPTIVE_EXCLUDE_SEEN_WITHIN_SESSIONS = SourcedValue(
    value=3,
    source="Short-term memory: recent session exclusion",
    notes="Questions from last 3 sessions excluded regardless of days. "
    "Prevents immediate repeats even if days threshold allows.",
    validated=False,
)

ADAPTIVE_MAX_REPEATS_IN_SESSION = SourcedValue(
    value=0,
    source="Session integrity: no duplicates within single session",
    notes="Each question appears at most once per session.",
    validated=True,
)

ADAPTIVE_ALLOW_REPEAT_IF_SUPPLY_LOW = SourcedValue(
    value=True,
    source="Graceful degradation: allow repeats when supply exhausted",
    notes="If exclusion filters leave too few questions, relax anti-repeat. "
    "Better to repeat than to under-serve the requested count.",
    validated=False,
)

# Revision Mode Constraints
ADAPTIVE_REVISION_DUE_RATIO_MIN = SourcedValue(
    value=0.60,
    source="Revision priority: minimum fraction from FSRS due concepts",
    notes="In revision mode, at least 60% of questions should target due concepts. "
    "Ensures revision sessions actually address forgetting.",
    validated=False,
)

ADAPTIVE_REVISION_DUE_RATIO_MAX = SourcedValue(
    value=0.85,
    source="Balance: leave room for reinforcement and new material",
    notes="Cap at 85% to allow some weak-concept questions even in revision mode.",
    validated=False,
)

ADAPTIVE_DUE_CONCEPT_FALLBACK_TO_WEAK = SourcedValue(
    value=True,
    source="Graceful fallback: if not enough due concepts, use weak concepts",
    notes="Prevents empty revision sessions when FSRS queue is small.",
    validated=True,
)

# Elo Challenge Band (target probability of correctness)
ADAPTIVE_P_LOW = SourcedValue(
    value=0.55,
    source="Desirable difficulty: lower bound for p(correct)",
    notes="Questions too easy (p > 0.85) waste time; too hard (p < 0.55) cause frustration. "
    "55% lower bound ensures manageable challenge. "
    "Reference: Bjork's desirable difficulties research suggests ~60-80% optimal.",
    validated=False,
)

ADAPTIVE_P_HIGH = SourcedValue(
    value=0.80,
    source="Desirable difficulty: upper bound for p(correct)",
    notes="80% upper bound ensures questions are still challenging. "
    "Within [0.55, 0.80] band optimizes learning efficiency.",
    validated=False,
)

ADAPTIVE_EXPLORE_NEW_QUESTION_RATE = SourcedValue(
    value=0.10,
    source="Exploration: fraction of questions from new/unrated pool",
    notes="10% of selection reserved for questions with insufficient Elo data. "
    "Helps calibrate new questions while maintaining session quality.",
    validated=False,
)

ADAPTIVE_EXPLORE_HIGH_UNCERTAINTY_RATE = SourcedValue(
    value=0.05,
    source="Uncertainty exploration: questions with high rating uncertainty",
    notes="5% reserved for questions where Elo uncertainty is high. "
    "Reduces uncertainty in item difficulty estimates.",
    validated=False,
)

# Base Priority Feature Weights
ADAPTIVE_W_WEAKNESS = SourcedValue(
    value=0.45,
    source="Priority weighting: weakness (1 - mastery) importance",
    notes="45% weight on weakness signal (low BKT mastery). "
    "Primary driver of theme selection for learning.",
    validated=False,
)

ADAPTIVE_W_DUE = SourcedValue(
    value=0.35,
    source="Priority weighting: FSRS due concepts importance",
    notes="35% weight on due concepts. "
    "Second priority: address forgetting before it happens.",
    validated=False,
)

ADAPTIVE_W_UNCERTAINTY = SourcedValue(
    value=0.10,
    source="Priority weighting: rating uncertainty importance",
    notes="10% weight on Elo uncertainty. "
    "Encourages exploring themes where user ability is uncertain.",
    validated=False,
)

ADAPTIVE_W_RECENCY_PENALTY = SourcedValue(
    value=0.10,
    source="Priority weighting: recency penalty importance",
    notes="10% penalty for recently practiced themes. "
    "Prevents over-focusing on same themes repeatedly.",
    validated=False,
)

ADAPTIVE_SUPPLY_MIN_QUESTIONS = SourcedValue(
    value=10,
    source="Minimum viable theme: questions needed to be selectable",
    notes="Theme must have at least 10 eligible questions (after exclusions). "
    "Prevents selecting themes with insufficient content.",
    validated=False,
)

# Reward Computation (Bandit Learning)
ADAPTIVE_REWARD_WINDOW = SourcedValue(
    value="session",
    source="Reward scope: compute reward after session completion",
    notes="Reward is computed once per session, not per question. "
    "Aggregates learning signal over the session.",
    validated=True,
)

ADAPTIVE_REWARD_TYPE = SourcedValue(
    value="bkt_delta",
    source="Reward signal: BKT mastery delta",
    notes="Reward = normalized mastery improvement on concepts in the theme. "
    "Direct measure of learning, not just correctness.",
    validated=True,
)

ADAPTIVE_REWARD_MIN_ATTEMPTS_PER_THEME = SourcedValue(
    value=3,
    source="Statistical reliability: minimum attempts to update Beta",
    notes="Only update Beta posterior if theme had >= 3 questions in session. "
    "Prevents noisy updates from low-exposure themes.",
    validated=False,
)

# =============================================================================
# Operational Constants
# =============================================================================

# Performance Sampling
PERF_SAMPLE_RATE = SourcedValue(
    value=0.05,
    source="Heuristic: 5% sampling rate for API performance tracking",
    notes="Sample 5% of requests to api_perf_sample table to manage volume. "
    "Can be adjusted via PERF_SAMPLE_RATE environment variable.",
    validated=False,
)

# Job System
JOB_LOCK_DURATION_MINUTES = SourcedValue(
    value=120,
    source="Heuristic: 2 hour lock duration for long-running jobs",
    notes="Job locks expire after 2 hours to prevent deadlocks from crashed processes.",
    validated=False,
)

REVISION_QUEUE_REGEN_BATCH_SIZE = SourcedValue(
    value=200,
    source="Heuristic: process 200 users per batch",
    notes="Chunk size for processing users in revision queue regeneration job. "
    "Balances memory usage and transaction size.",
    validated=False,
)

# FSRS Optimizer Trigger
FSRS_OPTIMIZER_COOLDOWN_DAYS = SourcedValue(
    value=7,
    source="Heuristic: weekly cooldown for FSRS training",
    notes="Minimum days between FSRS optimizer training runs per user. "
    "Prevents excessive training and allows time for new data to accumulate.",
    validated=False,
)

FSRS_AB_SPLIT_RATIO = SourcedValue(
    value=0.5,
    source="A/B testing: 50/50 split between baseline and tuned",
    notes="50% of eligible users get BASELINE_GLOBAL, 50% get TUNED_ELIGIBLE. "
    "Assignment is stable (seeded by user_id hash).",
    validated=True,
)

# Evaluation Harness
EVAL_CONFIDENCE_THRESHOLD = SourcedValue(
    value=0.5,
    source="Heuristic: conservative confidence threshold for model fallback",
    notes="If model prediction confidence < 0.5, fallback to v0 rules. "
    "Initially conservative; can be calibrated from validation data.",
    validated=False,
)

EVAL_REGRESSION_THRESHOLD_PCT = SourcedValue(
    value=0.10,
    source="Heuristic: 10% degradation threshold for regression detection",
    notes="If logloss increases by >10% vs baseline, flag as regression in shadow dashboard.",
    validated=False,
)

# =============================================================================
# IRT (Item Response Theory) - Shadow/Offline Calibration Only
# =============================================================================

# Priors (configurable; logged in dataset_spec or run config)
IRT_PRIOR_THETA_MEAN = SourcedValue(
    value=0.0,
    source="IRT convention: theta ~ N(0,1) standard scale",
    notes="Ability prior mean. Theta scale anchored via standardization post-fit.",
    validated=True,
)

IRT_PRIOR_THETA_SD = SourcedValue(
    value=1.0,
    source="IRT convention: theta ~ N(0,1)",
    notes="Ability prior standard deviation.",
    validated=True,
)

IRT_PRIOR_A_MEAN = SourcedValue(
    value=1.0,
    source="Heuristic: discrimination centered near 1",
    notes="Log-normal or transformed a prior mean. a > 0 via softplus.",
    validated=False,
)

IRT_PRIOR_B_MEAN = SourcedValue(
    value=0.0,
    source="Heuristic: difficulty centered at 0 (theta scale)",
    notes="Difficulty prior mean. Cold-start from ELO or p-value logit.",
    validated=False,
)

IRT_PRIOR_B_SD = SourcedValue(
    value=1.0,
    source="Heuristic: moderate spread",
    notes="Difficulty prior standard deviation.",
    validated=False,
)

# 3PL guessing: c in [0, 1/K], K = option_count
IRT_C_PRIOR_IMPLIED_BY_1K = SourcedValue(
    value=0.2,
    source="5-option MCQ: 1/5 = 0.2 guessing floor",
    notes="Default when K unknown. Otherwise use 1/option_count.",
    validated=True,
)

# Cold-start seeding
IRT_INIT_A_MODEST = SourcedValue(
    value=1.0,
    source="Prior mean; do not hardcode magic constants",
    notes="Initial a when no Elo/prior. Read from config.",
    validated=False,
)

IRT_LOW_DISCRIMINATION_THRESHOLD = SourcedValue(
    value=0.3,
    source="Heuristic: flag items with a < 0.3 for review",
    notes="Low discrimination -> flag low_discrimination.",
    validated=False,
)

# =============================================================================
# IRT Activation Policy Constants (Gate Thresholds)
# =============================================================================

# Gate A: Minimum Data Sufficiency
IRT_ACTIVATION_MIN_USERS = SourcedValue(
    value=500,
    source="IRT activation policy v1: minimum users for reliable calibration",
    notes="Cold-start blocker. IRT requires sufficient user diversity for stable parameter estimation.",
    validated=False,
)

IRT_ACTIVATION_MIN_ITEMS = SourcedValue(
    value=1000,
    source="IRT activation policy v1: minimum items for reliable calibration",
    notes="Cold-start blocker. Need sufficient item diversity for stable discrimination/difficulty estimates.",
    validated=False,
)

IRT_ACTIVATION_MIN_ATTEMPTS = SourcedValue(
    value=100000,
    source="IRT activation policy v1: minimum total attempts",
    notes="Cold-start blocker. Need large sample size for stable IRT parameter estimation.",
    validated=False,
)

IRT_ACTIVATION_MIN_ATTEMPTS_PER_ITEM = SourcedValue(
    value=50,
    source="IRT activation policy v1: minimum attempts per item (median)",
    notes="Ensures each item has sufficient data for reliable parameter estimation.",
    validated=False,
)

IRT_ACTIVATION_MIN_ATTEMPTS_PER_USER = SourcedValue(
    value=100,
    source="IRT activation policy v1: minimum attempts per user (median)",
    notes="Ensures each user has sufficient data for reliable ability estimation.",
    validated=False,
)

# Gate B: Holdout Predictive Superiority vs Baseline
IRT_ACTIVATION_DELTA_LOGLOSS = SourcedValue(
    value=0.005,
    source="IRT activation policy v1: minimum logloss improvement vs baseline",
    notes="IRT must improve logloss by at least 0.005 vs baseline (ELO+BKT+FSRS) to activate.",
    validated=False,
)

IRT_ACTIVATION_DELTA_BRIER = SourcedValue(
    value=0.003,
    source="IRT activation policy v1: minimum brier score improvement vs baseline",
    notes="IRT must improve brier score by at least 0.003 vs baseline to activate.",
    validated=False,
)

IRT_ACTIVATION_DELTA_ECE = SourcedValue(
    value=0.005,
    source="IRT activation policy v1: minimum ECE improvement vs baseline",
    notes="IRT must improve expected calibration error by at least 0.005 vs baseline to activate.",
    validated=False,
)

IRT_ACTIVATION_MIN_FOLDS = SourcedValue(
    value=3,
    source="IRT activation policy v1: minimum evaluation folds for stability",
    notes="Improvement must hold in at least 3 evaluation replays or time-sliced folds.",
    validated=False,
)

# Gate C: Calibration Sanity
IRT_ACTIVATION_A_MIN = SourcedValue(
    value=0.25,
    source="IRT activation policy v1: minimum discrimination threshold",
    notes="Items with a < A_MIN are flagged as 'too_low_a'.",
    validated=False,
)

IRT_ACTIVATION_B_ABS_MAX = SourcedValue(
    value=4.0,
    source="IRT activation policy v1: maximum absolute difficulty",
    notes="Items with |b| > B_ABS_MAX are flagged as 'b_out_of_range'.",
    validated=False,
)

IRT_ACTIVATION_MAX_PCT_LOW_A = SourcedValue(
    value=0.15,
    source="IRT activation policy v1: maximum percentage of items with low discrimination",
    notes="If >15% of items have a < A_MIN, gate fails.",
    validated=False,
)

IRT_ACTIVATION_MAX_PCT_C_CAP = SourcedValue(
    value=0.10,
    source="IRT activation policy v1: maximum percentage of items with c near cap (3PL only)",
    notes="If >10% of items have c > 0.95*(1/K), gate fails.",
    validated=False,
)

IRT_ACTIVATION_MAX_PCT_B_OOR = SourcedValue(
    value=0.05,
    source="IRT activation policy v1: maximum percentage of items with b out of range",
    notes="If >5% of items have |b| > B_ABS_MAX, gate fails.",
    validated=False,
)

# Gate D: Parameter Stability Over Time
IRT_ACTIVATION_MIN_CORR_B = SourcedValue(
    value=0.90,
    source="IRT activation policy v1: minimum Spearman correlation for difficulty (b)",
    notes="Difficulty parameters must correlate >= 0.90 with previous eligible run.",
    validated=False,
)

IRT_ACTIVATION_MIN_CORR_A = SourcedValue(
    value=0.80,
    source="IRT activation policy v1: minimum Spearman correlation for discrimination (a)",
    notes="Discrimination parameters must correlate >= 0.80 with previous eligible run.",
    validated=False,
)

IRT_ACTIVATION_MIN_CORR_C = SourcedValue(
    value=0.70,
    source="IRT activation policy v1: minimum Spearman correlation for guessing (c, 3PL only)",
    notes="Guessing parameters must correlate >= 0.70 with previous eligible run (3PL only).",
    validated=False,
)

IRT_ACTIVATION_MAX_MEDIAN_DELTA_B = SourcedValue(
    value=0.15,
    source="IRT activation policy v1: maximum median absolute delta for difficulty",
    notes="Median |delta_b| must be <= 0.15 to pass stability gate.",
    validated=False,
)

# Gate E: Measurement Precision (Information / SE)
IRT_ACTIVATION_MAX_MEDIAN_SE = SourcedValue(
    value=0.35,
    source="IRT activation policy v1: maximum median standard error for ability",
    notes="Median theta SE must be <= 0.35 for acceptable measurement precision.",
    validated=False,
)

IRT_ACTIVATION_MIN_PCT_SE_GOOD = SourcedValue(
    value=0.60,
    source="IRT activation policy v1: minimum percentage of users with SE below target",
    notes="At least 60% of users must have theta SE <= SE_TARGET.",
    validated=False,
)

IRT_ACTIVATION_SE_TARGET = SourcedValue(
    value=0.30,
    source="IRT activation policy v1: target standard error for ability",
    notes="Target SE for 'good' precision. Used in Gate E percentage calculation.",
    validated=False,
)

# Gate F: Coverage + Fairness Sanity
IRT_ACTIVATION_MAX_SUBGROUP_PENALTY = SourcedValue(
    value=0.02,
    source="IRT activation policy v1: maximum logloss penalty for subgroups",
    notes="No subgroup (year/block) can have logloss > overall + 0.02.",
    validated=False,
)


def get_adaptive_v1_defaults() -> dict:
    """Get Adaptive Selection v1 defaults as a dict."""
    return {
        # Beta prior
        "beta_prior_a": ADAPTIVE_BETA_PRIOR_A.value,
        "beta_prior_b": ADAPTIVE_BETA_PRIOR_B.value,
        "epsilon_floor": ADAPTIVE_EPSILON_FLOOR.value,
        # Theme selection
        "max_candidate_themes": ADAPTIVE_MAX_CANDIDATE_THEMES.value,
        "min_theme_count": ADAPTIVE_MIN_THEME_COUNT.value,
        "max_theme_count": ADAPTIVE_MAX_THEME_COUNT.value,
        "min_per_theme": ADAPTIVE_MIN_PER_THEME.value,
        "max_per_theme": ADAPTIVE_MAX_PER_THEME.value,
        # Repeat exclusion
        "exclude_seen_within_days": ADAPTIVE_EXCLUDE_SEEN_WITHIN_DAYS.value,
        "exclude_seen_within_sessions": ADAPTIVE_EXCLUDE_SEEN_WITHIN_SESSIONS.value,
        "max_repeats_in_session": ADAPTIVE_MAX_REPEATS_IN_SESSION.value,
        "allow_repeat_if_supply_low": ADAPTIVE_ALLOW_REPEAT_IF_SUPPLY_LOW.value,
        # Revision mode
        "revision_due_ratio_min": ADAPTIVE_REVISION_DUE_RATIO_MIN.value,
        "revision_due_ratio_max": ADAPTIVE_REVISION_DUE_RATIO_MAX.value,
        "due_concept_fallback_to_weak": ADAPTIVE_DUE_CONCEPT_FALLBACK_TO_WEAK.value,
        # Elo challenge band
        "p_low": ADAPTIVE_P_LOW.value,
        "p_high": ADAPTIVE_P_HIGH.value,
        "explore_new_question_rate": ADAPTIVE_EXPLORE_NEW_QUESTION_RATE.value,
        "explore_high_uncertainty_rate": ADAPTIVE_EXPLORE_HIGH_UNCERTAINTY_RATE.value,
        # Feature weights
        "w_weakness": ADAPTIVE_W_WEAKNESS.value,
        "w_due": ADAPTIVE_W_DUE.value,
        "w_uncertainty": ADAPTIVE_W_UNCERTAINTY.value,
        "w_recency_penalty": ADAPTIVE_W_RECENCY_PENALTY.value,
        "supply_min_questions": ADAPTIVE_SUPPLY_MIN_QUESTIONS.value,
        # Reward
        "reward_window": ADAPTIVE_REWARD_WINDOW.value,
        "reward_type": ADAPTIVE_REWARD_TYPE.value,
        "reward_min_attempts_per_theme": ADAPTIVE_REWARD_MIN_ATTEMPTS_PER_THEME.value,
    }
