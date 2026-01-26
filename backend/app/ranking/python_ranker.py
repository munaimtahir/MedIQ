"""Python baseline ranker — authoritative. Deterministic, stable tie-break by user_id."""

from __future__ import annotations

from uuid import UUID


def rank_by_percent(
    items: list[tuple[UUID, float]],
) -> list[tuple[UUID, int, float]]:
    """
    Compute rank (1=best) and percentile (0..100) from (user_id, percent) list.

    - Sort by percent desc; tie-break by user_id (stable, deterministic).
    - percentile = 100 * (1 - (rank - 1) / (n - 1)) for n > 1 else 100.

    Returns:
        List of (user_id, rank, percentile).
    """
    if not items:
        return []

    # Stable sort: percent desc, then user_id asc for determinism
    sorted_items = sorted(items, key=lambda x: (-x[1], str(x[0])))

    n = len(sorted_items)
    result: list[tuple[UUID, int, float]] = []

    for idx, (uid, _) in enumerate(sorted_items):
        rank = idx + 1
        if n > 1:
            percentile = 100.0 * (1.0 - (rank - 1) / (n - 1))
        else:
            percentile = 100.0
        result.append((uid, rank, percentile))

    return result
