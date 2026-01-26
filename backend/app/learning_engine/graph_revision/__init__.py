"""Graph-aware revision planning module.

Shadow-first module that re-ranks/augments FSRS revision plans using prerequisite
graph knowledge. Never affects student queues unless explicitly activated.
"""

from app.learning_engine.graph_revision.eligibility import is_graph_revision_eligible_for_activation
from app.learning_engine.graph_revision.planner import compute_shadow_revision_plan, get_planner_config

__all__ = [
    "compute_shadow_revision_plan",
    "get_planner_config",
    "is_graph_revision_eligible_for_activation",
]
