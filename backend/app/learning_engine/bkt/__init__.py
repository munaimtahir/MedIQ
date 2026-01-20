"""Bayesian Knowledge Tracing (BKT) module.

This module implements a production-grade BKT mastery engine with:
- Standard 4-parameter model (L0, T, S, G)
- Online mastery updates per attempt
- Batch training pipeline with EM via pyBKT
- Parameter constraints and degeneracy guards
- Full auditability via algo_version/algo_params/algo_runs
"""

from app.learning_engine.bkt.core import (
    apply_learning_transition,
    posterior_given_obs,
    predict_correct,
)

__all__ = [
    "predict_correct",
    "posterior_given_obs",
    "apply_learning_transition",
]
