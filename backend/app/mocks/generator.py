"""Deterministic mock question generator."""

import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.mocks.contracts import (
    CoverageItemCounts,
    CoverageItemWeights,
    MockBlueprintConfig,
)
from app.models.mock import MockBlueprint
from app.models.question_cms import Question, QuestionStatus


def generate_mock_questions(
    db: Session,
    blueprint: MockBlueprint,
    config: MockBlueprintConfig,
    seed: int,
    now: datetime,
) -> tuple[list[str], dict[str, Any], list[dict[str, Any]]]:
    """
    Generate mock questions deterministically.

    Args:
        db: Database session
        blueprint: Mock blueprint
        config: Blueprint configuration
        seed: Seed for deterministic RNG
        now: Current timestamp

    Returns:
        Tuple of (question_ids, meta, warnings)
        - question_ids: List of question ID strings (ordered)
        - meta: Metadata dict with coverage, distributions, etc.
        - warnings: List of warning dicts
    """
    rng = random.Random(seed)
    warnings: list[dict[str, Any]] = []

    # Step 1: Build candidate pool
    candidate_pool = _build_candidate_pool(
        db, blueprint, config, now, warnings
    )

    # Step 2: Apply anti-repeat
    # Note: blueprint.year is an int at runtime, but type checker sees Column[int]
    blueprint_year = cast(int, blueprint.year)
    excluded_by_anti_repeat = _apply_anti_repeat(
        db, candidate_pool, config.anti_repeat_policy, blueprint_year, now
    )
    candidate_pool = [q for q in candidate_pool if q["id"] not in excluded_by_anti_repeat]

    # Step 3: Allocate per theme
    # Note: blueprint.total_questions is an int at runtime, but type checker sees Column[int]
    total_q = cast(int, blueprint.total_questions)
    theme_allocations = _allocate_per_theme(
        config, total_q, rng, warnings
    )

    # Step 4: Select questions per theme bucket
    selected_questions: list[dict[str, Any]] = []
    coverage_achieved: dict[str, int] = {}
    difficulty_achieved: dict[str, int] = defaultdict(int)
    cognitive_achieved: dict[str, int] = defaultdict(int)

    for theme_id, count in theme_allocations.items():
        theme_candidates = [q for q in candidate_pool if str(q.get("theme_id")) == str(theme_id)]

        if not theme_candidates:
            warnings.append({
                "type": "theme_no_candidates",
                "theme_id": theme_id,
                "requested_count": count,
            })
            continue

        # Sample within theme respecting difficulty/cognitive mix
        theme_selected = _sample_within_theme(
            theme_candidates,
            count,
            config.difficulty_mix,
            config.cognitive_mix,
            rng,
            warnings,
        )

        selected_questions.extend(theme_selected)
        coverage_achieved[theme_id] = len(theme_selected)

        # Track distributions
        for q in theme_selected:
            if q.get("difficulty"):
                difficulty_achieved[q["difficulty"]] += 1
            if q.get("cognitive_level"):
                cognitive_achieved[q["cognitive_level"]] += 1

    # Step 5: Backfill if needed
    # Note: blueprint.total_questions is an int at runtime, but type checker sees Column[int]
    total_questions = cast(int, blueprint.total_questions)
    selected_count = len(selected_questions)
    if selected_count < total_questions:
        shortfall = total_questions - selected_count
        blueprint_year = cast(int, blueprint.year)
        backfilled = _backfill_questions(
            db,
            candidate_pool,
            selected_questions,
            shortfall,
            config,
            blueprint_year,
            rng,
            warnings,
        )
        selected_questions.extend(backfilled)
        warnings.append({
            "type": "coverage_underfilled",
            "requested": blueprint.total_questions,
            "achieved": len(selected_questions),
            "shortfall": shortfall,
        })

    # Step 6: Final ordering (stable by theme_id, difficulty_bucket, question_id)
    selected_questions.sort(key=lambda q: (
        q.get("theme_id", 0),
        _difficulty_bucket(q.get("difficulty", "")),
        str(q["id"]),
    ))

    question_ids = [str(q["id"]) for q in selected_questions]

    # Build meta
    meta: dict[str, Any] = {
        "coverage_achieved": coverage_achieved,
        "difficulty_distribution": dict(difficulty_achieved),
        "cognitive_distribution": dict(cognitive_achieved),
        "total_candidates_per_theme": {
            theme_id: len([q for q in candidate_pool if str(q.get("theme_id")) == str(theme_id)])
            for theme_id in theme_allocations.keys()
        },
        "excluded_by_anti_repeat": len(excluded_by_anti_repeat),
        "total_selected": len(question_ids),
    }

    return question_ids, meta, warnings


def _build_candidate_pool(
    db: Session,
    blueprint: MockBlueprint,
    config: MockBlueprintConfig,
    now: datetime,
    warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build candidate question pool from Postgres."""
    # Base query: PUBLISHED questions matching year
    query = db.query(
        Question.id,
        Question.theme_id,
        Question.difficulty,
        Question.cognitive_level,
        Question.source_book,
    ).filter(
        Question.status == QuestionStatus.PUBLISHED,
        Question.year_id == blueprint.year,
    )

    # Filter by coverage themes
    theme_ids = []
    if config.coverage.mode == "counts":
        theme_ids = [
            int(item.theme_id)
            for item in config.coverage.items
            if isinstance(item, CoverageItemCounts)
        ]
    else:
        theme_ids = [
            int(item.theme_id)
            for item in config.coverage.items
            if isinstance(item, CoverageItemWeights)
        ]

    if theme_ids:
        query = query.filter(Question.theme_id.in_(theme_ids))

    # Apply source constraints
    if config.source_constraints.allow_sources:
        query = query.filter(Question.source_book.in_(config.source_constraints.allow_sources))
    if config.source_constraints.deny_sources:
        query = query.filter(~Question.source_book.in_(config.source_constraints.deny_sources))

    # Apply tag constraints (must_include)
    must_include_themes = config.tag_constraints.must_include.get("theme_ids")
    if must_include_themes:
        must_include_theme_ints = [int(tid) for tid in must_include_themes]
        query = query.filter(Question.theme_id.in_(must_include_theme_ints))

    # Apply must_exclude question_ids
    must_exclude_question_ids = config.tag_constraints.must_exclude.get("question_ids")
    if must_exclude_question_ids:
        exclude_ids = [UUID(qid) for qid in must_exclude_question_ids]
        query = query.filter(~Question.id.in_(exclude_ids))

    # Order for deterministic selection
    query = query.order_by(Question.theme_id, Question.difficulty, Question.id)

    results = query.all()
    candidates = [
        {
            "id": row.id,
            "theme_id": row.theme_id,
            "difficulty": row.difficulty,
            "cognitive_level": row.cognitive_level,
            "source_book": row.source_book,
        }
        for row in results
    ]

    return candidates


def _apply_anti_repeat(
    db: Session,
    candidate_pool: list[dict[str, Any]],
    policy: Any,
    year: int,
    now: datetime,
) -> set[UUID]:
    """Apply anti-repeat policy and return excluded question IDs."""
    excluded: set[UUID] = set()

    if policy.avoid_days > 0:
        cutoff = now - timedelta(days=policy.avoid_days)
        # Query mock_instances created after cutoff
        from app.models.mock import MockInstance

        recent_instances = db.query(MockInstance).filter(
            MockInstance.year == year,
            MockInstance.created_at >= cutoff,
        ).all()

        for instance in recent_instances:
            question_ids_list = cast(list[str] | None, instance.question_ids)
            if question_ids_list:
                excluded.update(UUID(str(qid)) for qid in question_ids_list)

    # Note: avoid_last_n requires cohort context, which we don't have here
    # This would need user_id or cohort_key to implement

    return excluded


def _allocate_per_theme(
    config: MockBlueprintConfig,
    total_questions: int,
    rng: random.Random,
    warnings: list[dict[str, Any]],
) -> dict[str, int]:
    """Allocate question counts per theme."""
    allocations: dict[str, int] = {}

    if config.coverage.mode == "counts":
        for item in config.coverage.items:
            if isinstance(item, CoverageItemCounts):
                allocations[item.theme_id] = item.count
    else:
        # Weights mode: compute counts via round + remainder distribution
        weights = {
            item.theme_id: item.weight
            for item in config.coverage.items
            if isinstance(item, CoverageItemWeights)
        }
        total_weight = sum(weights.values())

        if abs(total_weight - 1.0) > 0.01:
            warnings.append({
                "type": "weights_sum_not_one",
                "total_weight": total_weight,
            })

        # Allocate proportionally
        allocated = 0
        for theme_id, weight in weights.items():
            count = round(weight * total_questions)
            allocations[theme_id] = count
            allocated += count

        # Distribute remainder
        remainder = total_questions - allocated
        if remainder != 0:
            theme_ids = list(allocations.keys())
            rng.shuffle(theme_ids)  # Deterministic shuffle
            for i in range(abs(remainder)):
                if remainder > 0:
                    allocations[theme_ids[i % len(theme_ids)]] += 1
                else:
                    if allocations[theme_ids[i % len(theme_ids)]] > 0:
                        allocations[theme_ids[i % len(theme_ids)]] -= 1

    return allocations


def _sample_within_theme(
    candidates: list[dict[str, Any]],
    count: int,
    difficulty_mix: Any,
    cognitive_mix: Any,
    rng: random.Random,
    warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sample questions within a theme respecting difficulty/cognitive mix."""
    if len(candidates) < count:
        # Not enough candidates, return all
        return candidates

    # Group by difficulty and cognitive level
    by_difficulty: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cognitive: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for q in candidates:
        diff = q.get("difficulty", "unknown")
        cog = q.get("cognitive_level", "unknown")
        by_difficulty[diff].append(q)
        by_cognitive[cog].append(q)

    # Allocate by difficulty mix
    difficulty_targets = {
        "easy": round(difficulty_mix.easy * count),
        "medium": round(difficulty_mix.medium * count),
        "hard": round(difficulty_mix.hard * count),
    }

    selected: list[dict[str, Any]] = []
    selected_ids: set[UUID] = set()

    # Try to satisfy difficulty mix (case-insensitive matching)
    difficulty_map = {
        "easy": ["easy", "EASY", "Easy"],
        "medium": ["medium", "MEDIUM", "Medium", "med", "MED", "Med"],
        "hard": ["hard", "HARD", "Hard"],
    }
    
    for diff_level, target_count in difficulty_targets.items():
        # Collect candidates matching this difficulty level (case-insensitive)
        matching_candidates = []
        for q in candidates:
            if q["id"] not in selected_ids:
                q_diff = (q.get("difficulty") or "").lower()
                if any(d.lower() in q_diff or q_diff in d.lower() for d in difficulty_map.get(diff_level, [])):
                    matching_candidates.append(q)
        
        rng.shuffle(matching_candidates)  # Deterministic shuffle
        take = min(target_count, len(matching_candidates))
        for q in matching_candidates[:take]:
            selected.append(q)
            selected_ids.add(q["id"])

    # Fill remaining with any available
    remaining = count - len(selected)
    if remaining > 0:
        available = [q for q in candidates if q["id"] not in selected_ids]
        rng.shuffle(available)
        for q in available[:remaining]:
            selected.append(q)
            selected_ids.add(q["id"])

    # If still not enough, warn and return what we have
    if len(selected) < count:
        warnings.append({
            "type": "theme_insufficient_candidates",
            "requested": count,
            "available": len(candidates),
            "selected": len(selected),
        })

    return selected


def _backfill_questions(
    db: Session,
    candidate_pool: list[dict[str, Any]],
    already_selected: list[dict[str, Any]],
    shortfall: int,
    config: MockBlueprintConfig,
    year: int,
    rng: random.Random,
    warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Backfill questions from same block/year ignoring difficulty/cognitive."""
    selected_ids = {q["id"] for q in already_selected}

    # Get all questions from same year, excluding already selected and must_exclude
    query = db.query(
        Question.id,
        Question.theme_id,
        Question.difficulty,
        Question.cognitive_level,
    ).filter(
        Question.status == QuestionStatus.PUBLISHED,
        Question.year_id == year,
        ~Question.id.in_(list(selected_ids)),
    )

    if config.tag_constraints.must_exclude.get("question_ids"):
        exclude_ids = [UUID(qid) for qid in config.tag_constraints.must_exclude["question_ids"]]
        query = query.filter(~Question.id.in_(exclude_ids))

    query = query.order_by(Question.theme_id, Question.id).limit(shortfall * 2)  # Get extra for safety

    results = query.all()
    backfill_candidates = [
        {
            "id": row.id,
            "theme_id": row.theme_id,
            "difficulty": row.difficulty,
            "cognitive_level": row.cognitive_level,
        }
        for row in results
    ]

    rng.shuffle(backfill_candidates)
    return backfill_candidates[:shortfall]


def _difficulty_bucket(difficulty: str | None) -> int:
    """Map difficulty to sortable bucket."""
    if not difficulty:
        return 99
    difficulty_lower = difficulty.lower()
    if "easy" in difficulty_lower:
        return 1
    elif "medium" in difficulty_lower or "med" in difficulty_lower:
        return 2
    elif "hard" in difficulty_lower:
        return 3
    return 99
