"""Mock exam ranking: Python baseline, Go shadow/active, parity harness (Task 145)."""

from app.ranking.python_ranker import rank_by_percent
from app.ranking.service import compute_ranking

__all__ = ["rank_by_percent", "compute_ranking"]
