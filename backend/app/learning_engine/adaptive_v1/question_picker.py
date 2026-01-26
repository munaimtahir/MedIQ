"""
Question picker for Adaptive Selection v1.

Selects individual questions within a theme using:
- FSRS due concepts (revision priority)
- BKT weak concepts (weakness priority)
- Elo challenge band (desirable difficulty)
- Exploration rate for new questions
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.learning_engine.adaptive_v1.core import create_seeded_rng

logger = logging.getLogger(__name__)


@dataclass
class QuestionCandidate:
    """Candidate question with selection metadata."""

    question_id: UUID
    concept_id: int | None
    difficulty_rating: float
    difficulty_uncertainty: float | None
    difficulty_attempts: int

    # Computed values
    p_correct: float = 0.5
    is_in_challenge_band: bool = True
    is_due_concept: bool = False
    is_weak_concept: bool = False
    is_new_question: bool = False
    priority_score: float = 0.0

    # Selection output
    selected: bool = False
    selection_reason: str = ""


@dataclass
class PickerResult:
    """Result of question picking for a theme."""

    theme_id: int
    quota: int
    selected_questions: list[UUID] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging."""
        return {
            "theme_id": self.theme_id,
            "quota": self.quota,
            "selected_count": len(self.selected_questions),
            "selected_questions": [str(q) for q in self.selected_questions],
            "stats": self.stats,
        }


def compute_p_correct(
    user_rating: float,
    question_rating: float,
    guess_floor: float,
    scale: float,
) -> float:
    """
    Compute probability of correct answer.

    p = g + (1 - g) * sigmoid((θ - b) / scale)

    Args:
        user_rating: User ability (θ)
        question_rating: Question difficulty (b)
        guess_floor: MCQ guess floor (g)
        scale: Logistic scale

    Returns:
        Probability in [g, 1]
    """
    import math

    diff = (user_rating - question_rating) / scale
    sigmoid = 1.0 / (1.0 + math.exp(-diff))
    p = guess_floor + (1.0 - guess_floor) * sigmoid
    return p


def is_in_challenge_band(p: float, p_low: float, p_high: float) -> bool:
    """
    Check if probability is within desirable difficulty band.

    Args:
        p: Predicted probability of correct
        p_low: Lower bound (e.g., 0.55)
        p_high: Upper bound (e.g., 0.80)

    Returns:
        True if p_low <= p <= p_high
    """
    return p_low <= p <= p_high


def pick_questions_for_theme(
    theme_id: int,
    quota: int,
    questions: list[dict],
    user_rating: float,
    due_concept_ids: set[int],
    weak_concept_ids: set[int],
    params: dict[str, Any],
    rng: random.Random,
) -> PickerResult:
    """
    Pick questions for a single theme.

    Selection priority:
    1. Due concepts (FSRS revision)
    2. Weak concepts (BKT mastery)
    3. Challenge band (Elo difficulty matching)
    4. Exploration (new/uncertain questions)

    Args:
        theme_id: Theme ID
        quota: Number of questions to select
        questions: Candidate questions from repo
        user_rating: User's global Elo rating
        due_concept_ids: Concepts due for review
        weak_concept_ids: Concepts with low mastery
        params: Algorithm parameters
        rng: Seeded RNG

    Returns:
        PickerResult with selected questions and stats
    """
    # Extract parameters
    guess_floor = params.get("guess_floor", 0.20)
    scale = params.get("scale", 400.0)
    p_low = params.get("p_low", 0.55)
    p_high = params.get("p_high", 0.80)
    explore_new_rate = params.get("explore_new_question_rate", 0.10)
    explore_unc_rate = params.get("explore_high_uncertainty_rate", 0.05)
    min_attempts_for_rated = 5  # Questions with fewer attempts are "new"

    # Convert to candidates
    candidates: list[QuestionCandidate] = []
    for q in questions:
        candidate = QuestionCandidate(
            question_id=q["question_id"],
            concept_id=q.get("concept_id"),
            difficulty_rating=q.get("difficulty_rating", 0.0),
            difficulty_uncertainty=q.get("difficulty_uncertainty"),
            difficulty_attempts=q.get("difficulty_attempts", 0),
        )

        # Compute p(correct)
        candidate.p_correct = compute_p_correct(
            user_rating,
            candidate.difficulty_rating,
            guess_floor,
            scale,
        )

        # Check challenge band
        candidate.is_in_challenge_band = is_in_challenge_band(
            candidate.p_correct, p_low, p_high
        )

        # Check if concept is due or weak
        if candidate.concept_id is not None:
            candidate.is_due_concept = candidate.concept_id in due_concept_ids
            candidate.is_weak_concept = candidate.concept_id in weak_concept_ids

        # Check if question is new/unrated
        candidate.is_new_question = candidate.difficulty_attempts < min_attempts_for_rated

        candidates.append(candidate)

    if not candidates:
        return PickerResult(theme_id=theme_id, quota=quota, stats={"empty_candidates": True})

    # Compute selection slots
    n_explore_new = max(1, int(quota * explore_new_rate))
    n_explore_unc = max(1, int(quota * explore_unc_rate))
    n_regular = quota - n_explore_new - n_explore_unc

    selected: list[UUID] = []
    selected_set: set[UUID] = set()
    stats = {
        "total_candidates": len(candidates),
        "in_challenge_band": sum(1 for c in candidates if c.is_in_challenge_band),
        "due_concepts": sum(1 for c in candidates if c.is_due_concept),
        "weak_concepts": sum(1 for c in candidates if c.is_weak_concept),
        "new_questions": sum(1 for c in candidates if c.is_new_question),
        "selected_due": 0,
        "selected_weak": 0,
        "selected_band": 0,
        "selected_explore": 0,
    }

    def select_candidate(c: QuestionCandidate, reason: str) -> bool:
        """Try to select a candidate."""
        if c.question_id in selected_set:
            return False
        c.selected = True
        c.selection_reason = reason
        selected.append(c.question_id)
        selected_set.add(c.question_id)
        return True

    # Priority 1: Due concepts (for revision mode)
    due_candidates = [c for c in candidates if c.is_due_concept and c.is_in_challenge_band]
    rng.shuffle(due_candidates)
    for c in due_candidates:
        if len(selected) >= n_regular:
            break
        if select_candidate(c, "due_concept"):
            stats["selected_due"] += 1

    # Priority 2: Weak concepts
    weak_candidates = [
        c for c in candidates
        if c.is_weak_concept and not c.selected and c.is_in_challenge_band
    ]
    rng.shuffle(weak_candidates)
    for c in weak_candidates:
        if len(selected) >= n_regular:
            break
        if select_candidate(c, "weak_concept"):
            stats["selected_weak"] += 1

    # Priority 3: Questions in challenge band
    band_candidates = [c for c in candidates if c.is_in_challenge_band and not c.selected]
    # Sort by how centered they are in the band
    band_center = (p_low + p_high) / 2
    band_candidates.sort(key=lambda c: abs(c.p_correct - band_center))
    for c in band_candidates:
        if len(selected) >= n_regular:
            break
        if select_candidate(c, "challenge_band"):
            stats["selected_band"] += 1

    # Priority 4: Exploration - new questions
    new_candidates = [c for c in candidates if c.is_new_question and not c.selected]
    rng.shuffle(new_candidates)
    for c in new_candidates:
        if len(selected) >= n_regular + n_explore_new:
            break
        if select_candidate(c, "explore_new"):
            stats["selected_explore"] += 1

    # Priority 5: Exploration - high uncertainty questions
    unc_candidates = [
        c for c in candidates
        if not c.selected
        and c.difficulty_uncertainty is not None
        and c.difficulty_uncertainty > 100  # Threshold for "high" uncertainty
    ]
    unc_candidates.sort(key=lambda c: c.difficulty_uncertainty or 0, reverse=True)
    for c in unc_candidates:
        if len(selected) >= quota:
            break
        if select_candidate(c, "explore_uncertainty"):
            stats["selected_explore"] += 1

    # Fallback: Fill remaining with any available questions
    remaining_candidates = [c for c in candidates if not c.selected]
    rng.shuffle(remaining_candidates)
    for c in remaining_candidates:
        if len(selected) >= quota:
            break
        if select_candidate(c, "fallback"):
            pass

    # Compute final stats
    selected_candidates = [c for c in candidates if c.selected]
    if selected_candidates:
        stats["avg_p_correct"] = sum(c.p_correct for c in selected_candidates) / len(
            selected_candidates
        )
        stats["difficulty_range"] = {
            "min": min(c.difficulty_rating for c in selected_candidates),
            "max": max(c.difficulty_rating for c in selected_candidates),
        }
    else:
        stats["avg_p_correct"] = 0.0
        stats["difficulty_range"] = {"min": 0.0, "max": 0.0}

    return PickerResult(
        theme_id=theme_id,
        quota=quota,
        selected_questions=selected,
        stats=stats,
    )


def pick_questions_for_all_themes(
    theme_quotas: list[tuple[int, int]],  # (theme_id, quota)
    questions_by_theme: dict[int, list[dict]],
    user_rating: float,
    due_concept_ids: set[int],
    weak_concept_ids: set[int],
    params: dict[str, Any],
    seed: str,
    interleave: bool = True,
) -> tuple[list[UUID], dict[str, Any]]:
    """
    Pick questions for all themes and merge results.

    Args:
        theme_quotas: List of (theme_id, quota) tuples
        questions_by_theme: Dict mapping theme_id -> candidate questions
        user_rating: User's global Elo rating
        due_concept_ids: Concepts due for review
        weak_concept_ids: Concepts with low mastery
        params: Algorithm parameters
        seed: Deterministic seed
        interleave: Whether to interleave questions across themes

    Returns:
        Tuple of (ordered question_ids, aggregate stats)
    """
    rng = create_seeded_rng(seed)

    results: list[PickerResult] = []
    all_selected: set[UUID] = set()

    for theme_id, quota in theme_quotas:
        questions = questions_by_theme.get(theme_id, [])

        # Filter out already selected questions (prevent duplicates across themes)
        filtered_questions = [q for q in questions if q["question_id"] not in all_selected]

        result = pick_questions_for_theme(
            theme_id=theme_id,
            quota=quota,
            questions=filtered_questions,
            user_rating=user_rating,
            due_concept_ids=due_concept_ids,
            weak_concept_ids=weak_concept_ids,
            params=params,
            rng=rng,
        )

        results.append(result)
        all_selected.update(result.selected_questions)

    # Merge question IDs
    if interleave:
        # Round-robin interleave across themes
        final_questions = interleave_questions(results)
    else:
        # Concatenate by theme order
        final_questions = []
        for result in results:
            final_questions.extend(result.selected_questions)

    # Aggregate stats
    aggregate_stats = {
        "total_selected": len(final_questions),
        "themes_used": [r.theme_id for r in results if r.selected_questions],
        "per_theme_stats": {r.theme_id: r.stats for r in results},
        "due_coverage": sum(r.stats.get("selected_due", 0) for r in results),
        "weak_coverage": sum(r.stats.get("selected_weak", 0) for r in results),
        "explore_count": sum(r.stats.get("selected_explore", 0) for r in results),
    }

    # Compute aggregate avg p
    all_p = []
    for r in results:
        if "avg_p_correct" in r.stats and r.selected_questions:
            all_p.extend([r.stats["avg_p_correct"]] * len(r.selected_questions))
    if all_p:
        aggregate_stats["avg_p_correct"] = sum(all_p) / len(all_p)

    return final_questions, aggregate_stats


def interleave_questions(results: list[PickerResult]) -> list[UUID]:
    """
    Interleave questions from multiple themes in round-robin fashion.

    Args:
        results: Picker results for each theme

    Returns:
        Interleaved list of question IDs
    """
    # Create iterators for each theme
    iterators = [iter(r.selected_questions) for r in results if r.selected_questions]

    if not iterators:
        return []

    interleaved: list[UUID] = []
    while iterators:
        # Remove empty iterators
        active_iterators = []
        for it in iterators:
            try:
                question_id = next(it)
                interleaved.append(question_id)
                active_iterators.append(it)
            except StopIteration:
                pass
        iterators = active_iterators

    return interleaved
