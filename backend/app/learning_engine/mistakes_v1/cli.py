"""CLI entry point for Mistake Engine v1 training."""

import asyncio
import logging
import sys
from datetime import date
from uuid import UUID

import click
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.learning_engine.mistakes_v1.schemas import CalibrationType, ModelType, TrainingConfig
from app.learning_engine.mistakes_v1.train import train_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--start", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", required=True, help="End date (YYYY-MM-DD)")
@click.option("--model", type=click.Choice(["logreg", "lgbm"]), default="lgbm", help="Model type")
@click.option("--calibration", type=click.Choice(["none", "sigmoid", "isotonic"]), default="isotonic", help="Calibration method")
@click.option("--train-split", type=float, default=0.8, help="Train/val split ratio")
@click.option("--user-id", help="User ID who triggered training (optional)")
@click.option("--notes", help="Optional notes for this training run")
def train(
    start: str,
    end: str,
    model: str,
    calibration: str,
    train_split: float,
    user_id: str | None,
    notes: str | None,
):
    """
    Train a Mistake Engine v1 model.

    Example:
        python -m app.learning_engine.mistakes_v1.cli train \\
            --start 2024-01-01 \\
            --end 2024-12-31 \\
            --model lgbm \\
            --calibration isotonic
    """
    # Parse dates
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError as e:
        click.echo(f"Invalid date format: {e}", err=True)
        sys.exit(1)

    # Parse model type
    model_type = ModelType.LOGREG if model == "logreg" else ModelType.LGBM

    # Parse calibration
    calibration_map = {
        "none": CalibrationType.NONE,
        "sigmoid": CalibrationType.SIGMOID,
        "isotonic": CalibrationType.ISOTONIC,
    }
    calibration_type = calibration_map[calibration]

    # Parse user_id
    user_uuid = UUID(user_id) if user_id else None

    # Create config
    config = TrainingConfig(
        start_date=start_date,
        end_date=end_date,
        model_type=model_type,
        calibration_type=calibration_type,
        train_split=train_split,
        notes=notes,
    )

    # Run training
    async def run_training():
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            try:
                model_version_id, metrics = await train_model(db, config, user_uuid)
                click.echo(f"Training completed successfully!")
                click.echo(f"Model version ID: {model_version_id}")
                click.echo(f"Metrics: {metrics.model_dump_json(indent=2)}")
            except Exception as e:
                logger.error(f"Training failed: {e}", exc_info=True)
                click.echo(f"Training failed: {e}", err=True)
                sys.exit(1)

    asyncio.run(run_training())


if __name__ == "__main__":
    train()
