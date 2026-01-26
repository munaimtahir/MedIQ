"""
Core algorithms for Adaptive Selection v1.

Implements:
- Thompson Sampling for theme selection
- Base priority computation from BKT/FSRS/Elo signals
- Quota allocation with constraints
- Deterministic seeded RNG for reproducibility
"""

import hashlib
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ThemeCandidate:
    """Candidate theme with computed features and scores."""

    theme_id: int
    title: str
    block_id: int

    # Feature values
    mastery: float = 0.5  # BKT mastery [0,1]
    weakness: float = 0.5  # 1 - mastery
    due_ratio: float = 0.0  # Fraction of concepts due
    uncertainty: float = 0.5  # Normalized Elo uncertainty
    recency_penalty: float = 0.0  # Penalty for recent practice
    supply: int = 0  # Available questions

    # Bandit state
    beta_a: float = 1.0
    beta_b: float = 1.0
    sampled_y: float = 0.5  # Thompson sample

    # Computed scores
    base_priority: float = 0.0
    final_score: float = 0.0

    # Selection output
    selected: bool = False
    quota: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging."""
        return {
            "theme_id": self.theme_id,
            "title": self.title,
            "mastery": round(self.mastery, 3),
            "weakness": round(self.weakness, 3),
            "due_ratio": round(self.due_ratio, 3),
            "uncertainty": round(self.uncertainty, 3),
            "recency_penalty": round(self.recency_penalty, 3),
            "supply": self.supply,
            "beta_a": round(self.beta_a, 3),
            "beta_b": round(self.beta_b, 3),
            "sampled_y": round(self.sampled_y, 4),
            "base_priority": round(self.base_priority, 4),
            "final_score": round(self.final_score, 4),
            "selected": self.selected,
            "quota": self.quota,
        }


@dataclass
class SelectionPlan:
    """Result of theme selection and quota allocation."""

    themes: list[ThemeCandidate] = field(default_factory=list)
    total_quota: int = 0
    seed: str = ""

    def selected_themes(self) -> list[ThemeCandidate]:
        """Get only selected themes."""
        return [t for t in self.themes if t.selected]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging."""
        return {
            "themes": [t.to_dict() for t in self.selected_themes()],
            "total_quota": self.total_quota,
            "seed": self.seed,
        }


def create_deterministic_seed(
    user_id: UUID,
    mode: str,
    count: int,
    block_ids: list[int],
    theme_ids: list[int] | None,
    date_bucket: str | None = None,
) -> str:
    """
    Create a deterministic seed for reproducible selection.

    Same inputs on the same day produce the same selection.

    Args:
        user_id: User ID
        mode: Session mode
        count: Requested count
        block_ids: Block IDs (sorted)
        theme_ids: Theme IDs filter (sorted) or None
        date_bucket: Date string (defaults to today)

    Returns:
        Hex seed string
    """
    if date_bucket is None:
        date_bucket = datetime.utcnow().strftime("%Y-%m-%d")

    # Normalize inputs
    sorted_blocks = sorted(block_ids)
    sorted_themes = sorted(theme_ids) if theme_ids else []

    components = [
        str(user_id),
        mode,
        str(count),
        ",".join(str(b) for b in sorted_blocks),
        ",".join(str(t) for t in sorted_themes),
        date_bucket,
    ]

    combined = "|".join(components)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def create_seeded_rng(seed: str) -> random.Random:
    """
    Create a seeded random number generator.

    Args:
        seed: Seed string (can be any string, will be hashed to hex)

    Returns:
        Seeded Random instance
    """
    # If seed is already hex, try to use it directly, otherwise hash it
    try:
        seed_int = int(seed, 16)
    except ValueError:
        # Not a valid hex string, hash it to get a deterministic integer
        import hashlib
        seed_bytes = hashlib.sha256(seed.encode()).digest()
        seed_int = int.from_bytes(seed_bytes[:8], byteorder='big')
    rng = random.Random(seed_int)
    return rng


def sample_beta(rng: random.Random, a: float, b: float) -> float:
    """
    Sample from Beta(a, b) distribution.

    Args:
        rng: Seeded RNG
        a: Alpha parameter (>0)
        b: Beta parameter (>0)

    Returns:
        Sample in [0, 1]
    """
    # Ensure positive parameters
    a = max(0.001, a)
    b = max(0.001, b)

    # Use beta variate from random module
    return rng.betavariate(a, b)


def compute_base_priority(
    weakness: float,
    due_ratio: float,
    uncertainty: float,
    recency_penalty: float,
    supply: int,
    params: dict[str, Any],
) -> float:
    """
    Compute base priority score for a theme.

    Base priority combines multiple signals with configurable weights.

    Args:
        weakness: 1 - mastery [0,1]
        due_ratio: Fraction of concepts due [0,1]
        uncertainty: Normalized uncertainty [0,1]
        recency_penalty: Recent practice penalty [0,1]
        supply: Available questions
        params: Algorithm parameters

    Returns:
        Base priority score (non-negative)
    """
    w_weakness = params.get("w_weakness", 0.45)
    w_due = params.get("w_due", 0.35)
    w_uncertainty = params.get("w_uncertainty", 0.10)
    w_recency = params.get("w_recency_penalty", 0.10)
    supply_min = params.get("supply_min_questions", 10)

    # Compute weighted sum
    score = (
        w_weakness * weakness
        + w_due * due_ratio
        + w_uncertainty * uncertainty
        - w_recency * recency_penalty
    )

    # Supply bonus/penalty
    if supply < supply_min:
        # Penalize themes with low supply
        supply_factor = supply / max(1, supply_min)
        score *= supply_factor

    # Ensure non-negative
    return max(0.0, score)


def compute_final_score(
    base_priority: float,
    sampled_y: float,
    epsilon_floor: float,
) -> float:
    """
    Compute final selection score combining base priority with Thompson sample.

    final_score = base_priority * (epsilon_floor + sampled_y)

    Args:
        base_priority: Base priority from features
        sampled_y: Thompson sample from Beta posterior
        epsilon_floor: Minimum exploration factor

    Returns:
        Final score for selection
    """
    return base_priority * (epsilon_floor + sampled_y)


def select_themes(
    candidates: list[ThemeCandidate],
    rng: random.Random,
    params: dict[str, Any],
) -> list[ThemeCandidate]:
    """
    Select themes using Thompson Sampling.

    Steps:
    1. Sample y ~ Beta(a, b) for each theme
    2. Compute final_score = base_priority * (epsilon + y)
    3. Sort by final_score descending
    4. Select top themes respecting min/max constraints

    Args:
        candidates: List of theme candidates with features computed
        rng: Seeded RNG
        params: Algorithm parameters

    Returns:
        Candidates with selection status and sampled_y updated
    """
    epsilon_floor = params.get("epsilon_floor", 0.10)
    min_theme_count = params.get("min_theme_count", 2)
    max_theme_count = params.get("max_theme_count", 5)
    supply_min = params.get("supply_min_questions", 10)

    # Step 1 & 2: Sample and compute final scores
    for candidate in candidates:
        candidate.sampled_y = sample_beta(rng, candidate.beta_a, candidate.beta_b)
        candidate.final_score = compute_final_score(
            candidate.base_priority,
            candidate.sampled_y,
            epsilon_floor,
        )

    # Step 3: Sort by final score (descending)
    sorted_candidates = sorted(candidates, key=lambda c: c.final_score, reverse=True)

    # Step 4: Select themes with supply constraint
    selected_count = 0
    for candidate in sorted_candidates:
        if selected_count >= max_theme_count:
            break

        # Check supply constraint
        if candidate.supply >= supply_min:
            candidate.selected = True
            selected_count += 1
        elif selected_count < min_theme_count:
            # Relax supply constraint for minimum themes
            if candidate.supply > 0:
                candidate.selected = True
                selected_count += 1

    # If still below minimum, select any remaining with supply > 0
    if selected_count < min_theme_count:
        for candidate in sorted_candidates:
            if candidate.selected:
                continue
            if selected_count >= min_theme_count:
                break
            if candidate.supply > 0:
                candidate.selected = True
                selected_count += 1

    logger.debug(f"Selected {selected_count} themes from {len(candidates)} candidates")

    return candidates


def allocate_quotas(
    selected_themes: list[ThemeCandidate],
    total_count: int,
    params: dict[str, Any],
) -> list[ThemeCandidate]:
    """
    Allocate question quotas to selected themes.

    Distributes total_count proportionally by final_score,
    respecting min/max per-theme constraints.

    Args:
        selected_themes: Themes marked as selected
        total_count: Total questions to allocate
        params: Algorithm parameters

    Returns:
        Themes with quota field set
    """
    min_per_theme = params.get("min_per_theme", 3)
    max_per_theme = params.get("max_per_theme", 20)

    if not selected_themes:
        return []

    n_themes = len(selected_themes)

    # Compute total final_score for proportional allocation
    total_score = sum(t.final_score for t in selected_themes)
    if total_score <= 0:
        total_score = n_themes  # Fallback to equal distribution

    # Initial proportional allocation
    allocated = 0
    for theme in selected_themes:
        if total_score > 0:
            proportion = theme.final_score / total_score
        else:
            proportion = 1.0 / n_themes

        raw_quota = int(proportion * total_count)

        # Apply constraints
        quota = max(min_per_theme, min(max_per_theme, raw_quota))

        # Don't exceed supply
        quota = min(quota, theme.supply)

        theme.quota = quota
        allocated += quota

    # Distribute remaining (or reduce excess)
    remaining = total_count - allocated

    if remaining > 0:
        # Distribute extra to highest-scoring themes with capacity
        for theme in sorted(selected_themes, key=lambda t: t.final_score, reverse=True):
            if remaining <= 0:
                break
            extra_capacity = min(
                max_per_theme - theme.quota,
                theme.supply - theme.quota,
                remaining,
            )
            if extra_capacity > 0:
                theme.quota += extra_capacity
                remaining -= extra_capacity

    elif remaining < 0:
        # Need to reduce allocations
        excess = -remaining
        for theme in sorted(selected_themes, key=lambda t: t.final_score):
            if excess <= 0:
                break
            can_reduce = theme.quota - min_per_theme
            if can_reduce > 0:
                reduce_by = min(can_reduce, excess)
                theme.quota -= reduce_by
                excess -= reduce_by

    # Final validation
    final_total = sum(t.quota for t in selected_themes)
    logger.debug(
        f"Allocated {final_total} questions across {n_themes} themes "
        f"(requested: {total_count})"
    )

    return selected_themes


def run_theme_selection(
    candidates: list[ThemeCandidate],
    total_count: int,
    seed: str,
    params: dict[str, Any],
) -> SelectionPlan:
    """
    Run full theme selection pipeline.

    Args:
        candidates: Theme candidates with features populated
        total_count: Total questions requested
        seed: Deterministic seed
        params: Algorithm parameters

    Returns:
        SelectionPlan with selected themes and quotas
    """
    # Create seeded RNG
    rng = create_seeded_rng(seed)

    # Select themes via Thompson Sampling
    candidates = select_themes(candidates, rng, params)

    # Get selected themes
    selected = [c for c in candidates if c.selected]

    # Allocate quotas
    if selected:
        selected = allocate_quotas(selected, total_count, params)

    # Build plan
    plan = SelectionPlan(
        themes=candidates,
        total_quota=sum(t.quota for t in selected),
        seed=seed,
    )

    return plan


# =============================================================================
# Reward Computation for Bandit Updates
# =============================================================================


def compute_bkt_delta_reward(
    pre_mastery: float,
    post_mastery: float,
    ceiling: float = 1.0,
) -> float:
    """
    Compute normalized reward from BKT mastery delta.

    reward = clamp((post - pre) / max(0.01, ceiling - pre), 0, 1)

    This normalizes improvement relative to room for improvement.

    Args:
        pre_mastery: Mastery before session
        post_mastery: Mastery after session
        ceiling: Maximum mastery (default 1.0)

    Returns:
        Reward in [0, 1]
    """
    room_for_improvement = max(0.01, ceiling - pre_mastery)
    delta = post_mastery - pre_mastery
    normalized = delta / room_for_improvement

    # Clamp to [0, 1]
    return max(0.0, min(1.0, normalized))


def update_beta_posterior(
    a: float,
    b: float,
    reward: float,
) -> tuple[float, float]:
    """
    Update Beta posterior with observed reward.

    a += reward
    b += (1 - reward)

    Args:
        a: Current alpha
        b: Current beta
        reward: Observed reward [0, 1]

    Returns:
        Tuple of (new_a, new_b)
    """
    new_a = a + reward
    new_b = b + (1.0 - reward)

    # Ensure minimum values for numerical stability
    new_a = max(0.001, new_a)
    new_b = max(0.001, new_b)

    return new_a, new_b


def normalize_uncertainty(
    uncertainty: float | None,
    unc_init: float = 350.0,
    unc_floor: float = 50.0,
) -> float:
    """
    Normalize Elo uncertainty to [0, 1] range.

    Args:
        uncertainty: Raw uncertainty value
        unc_init: Initial uncertainty (max)
        unc_floor: Floor uncertainty (min)

    Returns:
        Normalized uncertainty [0, 1]
    """
    if uncertainty is None:
        return 1.0  # Unknown = maximum uncertainty

    # Clamp to valid range
    unc = max(unc_floor, min(unc_init, uncertainty))

    # Normalize
    normalized = (unc - unc_floor) / (unc_init - unc_floor)

    return normalized


def compute_recency_penalty(
    last_selected_at: datetime | None,
    now: datetime,
    decay_days: float = 7.0,
) -> float:
    """
    Compute recency penalty for recently practiced themes.

    Decays exponentially from 1.0 (just practiced) to 0.0 (long ago).

    Args:
        last_selected_at: When theme was last selected
        now: Current time
        decay_days: Half-life in days

    Returns:
        Penalty in [0, 1], higher = more recent
    """
    if last_selected_at is None:
        return 0.0  # Never selected = no penalty

    # Compute days since last selection
    if last_selected_at.tzinfo is None:
        # Handle naive datetime
        delta = now.replace(tzinfo=None) - last_selected_at
    else:
        delta = now - last_selected_at

    days = delta.total_seconds() / 86400

    # Exponential decay
    penalty = math.exp(-days / decay_days)

    return penalty
