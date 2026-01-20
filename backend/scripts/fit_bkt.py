#!/usr/bin/env python3
"""
CLI script to fit BKT parameters from historical data.

Usage:
    python -m scripts.fit_bkt --concept-id <uuid> [options]
    python -m scripts.fit_bkt --all-concepts [options]

Examples:
    # Fit parameters for a single concept
    python -m scripts.fit_bkt --concept-id 123e4567-e89b-12d3-a456-426614174000

    # Fit for all concepts with sufficient data
    python -m scripts.fit_bkt --all-concepts --min-attempts 20

    # Fit with custom date range and activate
    python -m scripts.fit_bkt --concept-id 123e4567-e89b-12d3-a456-426614174000 \
        --from-date 2025-01-01 --to-date 2026-01-01 --activate
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.learning import AlgoVersion
from app.learning_engine.constants import AlgoKey, AlgoStatus
from app.learning_engine.bkt.training import (
    build_training_dataset,
    fit_bkt_parameters,
    persist_fitted_params,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def get_active_bkt_version(db: AsyncSession) -> Optional[AlgoVersion]:
    """Get the active BKT algorithm version."""
    result = await db.execute(
        select(AlgoVersion).where(
            AlgoVersion.algo_key == AlgoKey.BKT, AlgoVersion.status == AlgoStatus.ACTIVE
        )
    )
    return result.scalar_one_or_none()


async def fit_concept(
    db: AsyncSession,
    concept_id: UUID,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    min_attempts: int,
    activate: bool,
    constraints: Optional[dict],
) -> tuple[bool, str]:
    """
    Fit BKT parameters for a single concept.

    Returns:
        Tuple of (success, message)
    """
    logger.info(f"Fitting BKT parameters for concept {concept_id}")

    # Get active BKT version
    algo_version = await get_active_bkt_version(db)
    if not algo_version:
        return False, "No active BKT algorithm version found"

    # Build training dataset
    logger.info(f"Building training dataset...")
    dataset = await build_training_dataset(
        db,
        concept_id,
        from_date=from_date,
        to_date=to_date,
        min_attempts_per_user=1,
    )

    # Check if sufficient data
    if not dataset.is_sufficient(min_attempts=min_attempts):
        summary = dataset.summary()
        return False, (
            f"Insufficient data: {summary['total_attempts']} attempts "
            f"from {summary['unique_users']} users (min={min_attempts})"
        )

    logger.info(f"Dataset: {dataset.summary()}")

    # Fit parameters
    logger.info("Fitting BKT parameters using EM...")
    params, metrics, is_valid, message = await fit_bkt_parameters(
        dataset,
        constraints=constraints,
        use_cross_validation=False,
    )

    if not is_valid:
        return False, f"Fitting failed: {message}"

    # Persist parameters
    logger.info("Persisting fitted parameters...")
    skill_params = await persist_fitted_params(
        db,
        concept_id=concept_id,
        params=params,
        metrics=metrics,
        algo_version_id=algo_version.id,
        from_date=from_date,
        to_date=to_date,
        constraints_applied=constraints or {},
        activate=activate,
    )

    await db.commit()

    success_msg = (
        f"Successfully fitted BKT parameters for concept {concept_id}\n"
        f"  L0={params['p_L0']:.3f}, T={params['p_T']:.3f}, "
        f"S={params['p_S']:.3f}, G={params['p_G']:.3f}\n"
        f"  Training samples: {metrics['training_samples']}\n"
        f"  Active: {activate}\n"
        f"  ID: {skill_params.id}"
    )

    return True, success_msg


async def fit_all_concepts(
    db: AsyncSession,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    min_attempts: int,
    activate: bool,
    constraints: Optional[dict],
) -> dict:
    """
    Fit BKT parameters for all concepts with sufficient data.

    Returns:
        Dict with success/failure counts and details
    """
    # TODO: Get all concept IDs from a concepts table
    # For now, this is a placeholder
    logger.warning("--all-concepts not yet implemented: requires concepts table")

    return {
        "total": 0,
        "success": 0,
        "failed": 0,
        "details": [],
    }


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fit BKT parameters from historical data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Target selection
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--concept-id",
        type=str,
        help="Concept ID to fit parameters for",
    )
    target_group.add_argument(
        "--all-concepts",
        action="store_true",
        help="Fit parameters for all concepts with sufficient data",
    )

    # Data selection
    parser.add_argument(
        "--from-date",
        type=str,
        help="Start date for training data (ISO format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to-date",
        type=str,
        help="End date for training data (ISO format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--min-attempts",
        type=int,
        default=10,
        help="Minimum total attempts required for fitting (default: 10)",
    )

    # Parameter constraints
    parser.add_argument(
        "--L0-min",
        type=float,
        default=0.001,
        help="Minimum value for L0 parameter (default: 0.001)",
    )
    parser.add_argument(
        "--L0-max",
        type=float,
        default=0.5,
        help="Maximum value for L0 parameter (default: 0.5)",
    )
    parser.add_argument(
        "--T-min",
        type=float,
        default=0.001,
        help="Minimum value for T parameter (default: 0.001)",
    )
    parser.add_argument(
        "--T-max",
        type=float,
        default=0.5,
        help="Maximum value for T parameter (default: 0.5)",
    )
    parser.add_argument(
        "--S-min",
        type=float,
        default=0.001,
        help="Minimum value for S parameter (default: 0.001)",
    )
    parser.add_argument(
        "--S-max",
        type=float,
        default=0.4,
        help="Maximum value for S parameter (default: 0.4)",
    )
    parser.add_argument(
        "--G-min",
        type=float,
        default=0.001,
        help="Minimum value for G parameter (default: 0.001)",
    )
    parser.add_argument(
        "--G-max",
        type=float,
        default=0.4,
        help="Maximum value for G parameter (default: 0.4)",
    )

    # Actions
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Mark fitted parameters as active (will deactivate previous params)",
    )

    args = parser.parse_args()

    # Parse dates
    from_date = None
    to_date = None

    if args.from_date:
        try:
            from_date = datetime.fromisoformat(args.from_date)
        except ValueError:
            logger.error(f"Invalid from-date format: {args.from_date}")
            return 1

    if args.to_date:
        try:
            to_date = datetime.fromisoformat(args.to_date)
        except ValueError:
            logger.error(f"Invalid to-date format: {args.to_date}")
            return 1

    # Build constraints dict
    constraints = {
        "L0_min": args.L0_min,
        "L0_max": args.L0_max,
        "T_min": args.T_min,
        "T_max": args.T_max,
        "S_min": args.S_min,
        "S_max": args.S_max,
        "G_min": args.G_min,
        "G_max": args.G_max,
    }

    # Run fitting
    async with AsyncSessionLocal() as db:
        if args.concept_id:
            try:
                concept_id = UUID(args.concept_id)
            except ValueError:
                logger.error(f"Invalid concept ID: {args.concept_id}")
                return 1

            success, message = await fit_concept(
                db,
                concept_id=concept_id,
                from_date=from_date,
                to_date=to_date,
                min_attempts=args.min_attempts,
                activate=args.activate,
                constraints=constraints,
            )

            if success:
                logger.info(message)
                return 0
            else:
                logger.error(message)
                return 1

        else:  # --all-concepts
            results = await fit_all_concepts(
                db,
                from_date=from_date,
                to_date=to_date,
                min_attempts=args.min_attempts,
                activate=args.activate,
                constraints=constraints,
            )

            logger.info(f"Fitted parameters for {results['success']}/{results['total']} concepts")

            if results["failed"] > 0:
                logger.warning(f"{results['failed']} concepts failed")
                for detail in results["details"]:
                    if not detail["success"]:
                        logger.warning(f"  {detail['concept_id']}: {detail['message']}")

            return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
