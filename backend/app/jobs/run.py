"""CLI entry point for job execution."""

import asyncio
import logging
import sys
from datetime import datetime

import click
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.jobs.fsrs_train_user import process_fsrs_training_job, train_fsrs_for_user
from app.jobs.revision_queue_regen import regenerate_revision_queues
from app.jobs.warehouse_incremental_export import run_warehouse_incremental_export

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.argument("job_key")
def run(job_key: str):
    """
    Run a scheduled job.

    Example:
        python -m app.jobs.run revision_queue_regen
    """
    async def run_async():
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            try:
                # Check exam mode (DB-backed) before running heavy jobs
                from app.system.flags import is_exam_mode
                from sqlalchemy.orm import Session
                # Convert async session to sync for is_exam_mode (it uses sync DB)
                from app.db.session import SessionLocal
                sync_db = SessionLocal()
                try:
                    if is_exam_mode(sync_db):
                        click.echo(f"Job {job_key} skipped: Exam mode is enabled", err=True)
                        sys.exit(0)
                finally:
                    sync_db.close()
                
                if job_key == "revision_queue_regen":
                    result = await regenerate_revision_queues(db, scheduled_for=datetime.utcnow())
                    click.echo(f"Job completed: {result}")
                elif job_key == "warehouse_incremental_export":
                    result = await run_warehouse_incremental_export(db, scheduled_for=datetime.utcnow())
                    click.echo(f"Job completed: {result}")
                elif job_key == "fsrs_train_user":
                    # For FSRS training, user_id should be passed as argument or in job metadata
                    # For CLI, we'd need to pass user_id as argument
                    click.echo("FSRS training requires user_id. Use API endpoint or pass as argument.", err=True)
                    sys.exit(1)
                else:
                    click.echo(f"Unknown job key: {job_key}", err=True)
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Job failed: {e}", exc_info=True)
                click.echo(f"Job failed: {e}", err=True)
                sys.exit(1)

    asyncio.run(run_async())


if __name__ == "__main__":
    run()
