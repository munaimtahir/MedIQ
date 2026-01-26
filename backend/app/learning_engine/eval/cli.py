"""CLI for evaluation harness."""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Any
from uuid import UUID

import click
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.learning_engine.eval.dataset import DatasetSpec
from app.learning_engine.eval.runner import run_evaluation
from app.learning_engine.eval.replay import EvalSuite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Placeholder suite implementation (would be replaced with actual suite)
class PlaceholderSuite(EvalSuite):
    """Placeholder suite for testing."""

    def predict(self, state, event_context):
        from app.learning_engine.eval.replay import ReplayPrediction

        return ReplayPrediction(event_id=event_context.event_id, p_correct=0.5)

    def update(self, state, outcome, event_context):
        return state

    def init_state(self, user_id):
        from app.learning_engine.eval.replay import ReplayState

        return ReplayState(user_id=user_id)


@click.group()
def cli():
    """Evaluation harness CLI."""
    pass


@cli.command()
@click.option("--suite", required=True, help="Suite name (e.g., bkt_v1)")
@click.option("--time-min", required=True, help="Start time (ISO format)")
@click.option("--time-max", required=True, help="End time (ISO format)")
@click.option("--split", type=click.Choice(["time", "user_holdout"]), default="time", help="Split strategy")
@click.option("--seed", type=int, help="Random seed")
@click.option("--notes", help="Optional notes")
def run(suite: str, time_min: str, time_max: str, split: str, seed: int | None, notes: str | None):
    """
    Run an evaluation.

    Example:
        python -m app.learning_engine.eval.cli run \\
            --suite bkt_v1 \\
            --time-min 2024-01-01T00:00:00Z \\
            --time-max 2024-12-31T23:59:59Z \\
            --split time \\
            --seed 42
    """
    # Parse times
    try:
        time_min_dt = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
        time_max_dt = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
    except ValueError as e:
        click.echo(f"Invalid time format: {e}", err=True)
        sys.exit(1)

    # Create dataset spec
    dataset_spec = DatasetSpec(
        time_min=time_min_dt,
        time_max=time_max_dt,
        split_strategy=split,
    )

    # Create config
    config = {
        "calibration_bins": 10,
        "mastery_threshold": 0.85,
        "store_traces": False,
    }

    # Create suite (placeholder - would load actual suite)
    suite_impl = PlaceholderSuite()

    # Run evaluation
    async def run_async():
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            try:
                run_id = await run_evaluation(
                    db,
                    suite=suite_impl,
                    suite_name=suite,
                    suite_versions={"bkt": "1.0.0"},  # Placeholder
                    dataset_spec=dataset_spec,
                    config=config,
                    random_seed=seed,
                    notes=notes,
                )
                click.echo(f"Evaluation run started: {run_id}")
            except Exception as e:
                logger.error(f"Evaluation failed: {e}", exc_info=True)
                click.echo(f"Evaluation failed: {e}", err=True)
                sys.exit(1)

    asyncio.run(run_async())


@cli.command()
@click.option("--suite", help="Filter by suite name")
@click.option("--status", help="Filter by status")
@click.option("--limit", type=int, default=20, help="Maximum results")
def list(suite: str | None, status: str | None, limit: int):
    """List evaluation runs."""
    async def list_async():
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            from app.learning_engine.eval.registry import list_eval_runs

            runs = await list_eval_runs(db, suite_name=suite, status=status, limit=limit)

            click.echo(f"{'ID':<40} {'Suite':<20} {'Status':<15} {'Created':<25}")
            click.echo("-" * 100)

            for run in runs:
                click.echo(
                    f"{str(run.id):<40} {run.suite_name:<20} {run.status:<15} {str(run.created_at):<25}"
                )

    asyncio.run(list_async())


@cli.command()
@click.argument("run_id")
def show(run_id: str):
    """Show details of an evaluation run."""
    async def show_async():
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            from app.learning_engine.eval.registry import get_eval_run
            from app.models.eval import EvalMetric
            from sqlalchemy import select

            run = await get_eval_run(db, UUID(run_id))
            if not run:
                click.echo(f"Run not found: {run_id}", err=True)
                sys.exit(1)

            click.echo(f"Run ID: {run.id}")
            click.echo(f"Suite: {run.suite_name}")
            click.echo(f"Status: {run.status}")
            click.echo(f"Created: {run.created_at}")
            click.echo(f"Started: {run.started_at}")
            click.echo(f"Finished: {run.finished_at}")
            click.echo("")

            # Get metrics
            stmt = select(EvalMetric).where(EvalMetric.run_id == run.id)
            result = await db.execute(stmt)
            metrics = result.scalars().all()

            click.echo("Metrics:")
            click.echo(f"{'Name':<30} {'Value':<15} {'N':<10} {'Scope':<20}")
            click.echo("-" * 75)

            for metric in metrics:
                scope_str = f"{metric.scope_type}"
                if metric.scope_id:
                    scope_str += f":{metric.scope_id}"
                click.echo(
                    f"{metric.metric_name:<30} {float(metric.value):<15.6f} {metric.n:<10} {scope_str:<20}"
                )

    asyncio.run(show_async())


if __name__ == "__main__":
    cli()
