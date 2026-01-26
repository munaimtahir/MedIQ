"""
Adaptive Selection v1 - Constrained Multi-Armed Bandit.

This module implements theme-level Thompson Sampling with constraints
for optimal question selection combining:
- BKT mastery signals (weakness)
- FSRS due concepts (forgetting prevention)
- Elo difficulty matching (desirable difficulty)
- User-specific learning yield optimization (bandit reward)
"""

from app.learning_engine.adaptive_v1.service import select_questions_v1

__all__ = ["select_questions_v1"]
