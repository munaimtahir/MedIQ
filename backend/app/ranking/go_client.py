"""Go ranking service client. Raises if disabled; used for shadow/active when enabled."""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoRankingDisabledError(Exception):
    """Raised when GO_RANKING_ENABLED is false."""


def check_go_ranking_health() -> bool:
    """
    Check Go ranking service health. Returns False if disabled or unreachable.
    """
    if not settings.GO_RANKING_ENABLED:
        return False
    base = settings.RANKING_GO_URL.rstrip("/")
    try:
        r = httpx.get(f"{base}/health", timeout=2.0)
        return r.status_code == 200
    except Exception as e:
        logger.debug("Go ranking health check failed: %s", e)
        return False


def rank_via_go(
    cohort_id: str,
    items: list[tuple[UUID, float]],
) -> list[tuple[UUID, int, float]]:
    """
    POST /rank to Go service. Returns list of (user_id, rank, percentile).

    Raises:
        GoRankingDisabledError: if GO_RANKING_ENABLED is false
        httpx.HTTPError: on request failure
    """
    if not settings.GO_RANKING_ENABLED:
        raise GoRankingDisabledError("GO_RANKING_ENABLED is false")

    base = settings.RANKING_GO_URL.rstrip("/")
    payload = {
        "cohort_id": cohort_id,
        "items": [{"user_id": str(uid), "percent": pct} for uid, pct in items],
    }

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(f"{base}/rank", json=payload)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for row in data.get("results", []):
        uid = UUID(row["user_id"])
        rank = int(row["rank"])
        pct = float(row["percentile"])
        results.append((uid, rank, pct))
    return results
