"""Utility functions for metrics computation."""

from typing import Any


def aggregate_by_scope(
    metrics: list[dict[str, Any]],
    scope_type: str,
    scope_id: str | None = None,
) -> dict[str, Any]:
    """
    Aggregate metrics by scope.

    Args:
        metrics: List of metric dictionaries
        scope_type: Scope type (GLOBAL, YEAR, BLOCK, THEME, CONCEPT, USER)
        scope_id: Scope identifier (optional)

    Returns:
        Aggregated metrics dictionary
    """
    # Filter by scope
    filtered = [
        m for m in metrics if m.get("scope_type") == scope_type and m.get("scope_id") == scope_id
    ]

    if not filtered:
        return {}

    # Aggregate (simplified - would do proper aggregation per metric type)
    return {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "count": len(filtered),
        "metrics": filtered,
    }
