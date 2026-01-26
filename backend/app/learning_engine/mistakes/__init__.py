"""Common mistakes identification algorithm."""

from app.learning_engine.mistakes.v0 import classify_session_mistakes_v0

compute_mistakes_v0 = classify_session_mistakes_v0
__all__ = ["compute_mistakes_v0", "classify_session_mistakes_v0"]
