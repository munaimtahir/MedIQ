"""Deterministic replay engine for learning algorithms."""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.learning_engine.eval.dataset import EvalEvent

logger = logging.getLogger(__name__)


class ReplayState(BaseModel):
    """State maintained during replay."""

    user_id: UUID
    # Algorithm-specific state (e.g., BKT mastery, Elo ratings)
    algo_state: dict[str, Any] = {}


class ReplayPrediction(BaseModel):
    """Prediction made before state update."""

    event_id: UUID | None = None
    p_correct: float | None = None  # Predicted probability of correctness
    p_mastery: float | None = None  # Predicted mastery (if BKT)
    p_retrievability: float | None = None  # Predicted retrievability (if FSRS)
    p_recall: float | None = None  # Predicted recall (if decay model)
    difficulty_match_quality: float | None = None  # If Elo/IRT proxy exists
    recommended_items: list[str] | None = None  # Recommended concepts/themes (if applicable)


class ReplayTrace(BaseModel):
    """Trace of replay execution."""

    predictions: list[ReplayPrediction] = []
    state_snapshots: list[ReplayState] = []  # Optional: store state at intervals
    aggregates: dict[str, Any] = {}  # Aggregate counters per scope


class EvalSuite(ABC):
    """Pluggable interface for learning algorithm suites."""

    @abstractmethod
    async def predict(
        self,
        state: ReplayState,
        event_context: EvalEvent,
    ) -> ReplayPrediction:
        """
        Compute predictions BEFORE state update.

        Args:
            state: Current algorithm state
            event_context: Event context (question, user, etc.)

        Returns:
            ReplayPrediction with all available predictions
        """
        pass

    @abstractmethod
    async def update(
        self,
        state: ReplayState,
        outcome: bool,
        event_context: EvalEvent,
    ) -> ReplayState:
        """
        Update algorithm state with ground-truth outcome.

        Args:
            state: Current algorithm state
            outcome: Ground-truth correctness (True/False)
            event_context: Event context

        Returns:
            Updated state
        """
        pass

    @abstractmethod
    def init_state(self, user_id: UUID) -> ReplayState:
        """
        Initialize state for a new user.

        Args:
            user_id: User ID

        Returns:
            Initial ReplayState
        """
        pass


async def replay_user_stream(
    events: list[EvalEvent],
    suite: EvalSuite,
    store_traces: bool = False,
) -> ReplayTrace:
    """
    Replay a user's event stream deterministically.

    Args:
        events: List of events for a single user (must be sorted by timestamp)
        suite: Algorithm suite to replay
        store_traces: Whether to store detailed traces (memory-intensive)

    Returns:
        ReplayTrace with predictions and aggregates
    """
    if not events:
        return ReplayTrace()

    user_id = events[0].user_id
    state = suite.init_state(user_id)

    trace = ReplayTrace()
    aggregates: dict[str, dict[str, Any]] = {}  # scope -> metric -> value

    for event in events:
        # Predict BEFORE update
        prediction = await suite.predict(state, event)
        trace.predictions.append(prediction)

        # Update state with ground-truth outcome
        if event.is_correct is not None:
            state = await suite.update(state, event.is_correct, event)

        # Aggregate metrics (simplified - would compute per scope)
        # This is a placeholder; actual aggregation happens in metrics modules

    trace.aggregates = aggregates
    return trace


def replay_dataset(
    events: Iterator[EvalEvent],
    suite: EvalSuite,
    store_traces: bool = False,
) -> dict[UUID, ReplayTrace]:
    """
    Replay entire dataset, grouped by user.

    Args:
        events: Iterator of events (should be sorted by user_id, timestamp)
        suite: Algorithm suite to replay
        store_traces: Whether to store detailed traces

    Returns:
        Dictionary mapping user_id -> ReplayTrace
    """
    # Group events by user
    user_events: dict[UUID, list[EvalEvent]] = {}
    for event in events:
        if event.user_id not in user_events:
            user_events[event.user_id] = []
        user_events[event.user_id].append(event)

    # Replay each user
    traces = {}
    for user_id, user_event_list in user_events.items():
        # Sort by timestamp
        user_event_list.sort(key=lambda e: e.timestamp)
        trace = replay_user_stream(user_event_list, suite, store_traces)
        traces[user_id] = trace

    return traces
