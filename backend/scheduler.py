import asyncio
import logging
import uuid
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from settings import config
from models.database import async_session, ExecutionLog
from graph import build_synapse_rader_graph, initial_state

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run_pipeline(trigger: str = "scheduled"):
    """Run the full Synapse_Rader pipeline."""
    run_id = uuid.uuid4().hex[:12]
    logger.info(f"Pipeline {run_id} started (trigger={trigger})")

    try:
        await _log_execution(run_id, trigger, "pipeline", "running")

        graph = build_synapse_rader_graph()
        state = initial_state(trigger=trigger)
        result = await graph.ainvoke(state, {"configurable": {"thread_id": run_id}})

        status = result.get("status", "?")
        raw_count = len(result.get("raw_items", []))
        logger.info(f"Pipeline {run_id} completed: status={status}, items={raw_count}")
        await _log_execution(run_id, trigger, "pipeline", status, raw_count)
    except Exception as e:
        logger.error(f"Pipeline {run_id} failed: {e}")
        await _log_execution(run_id, trigger, "pipeline", "failed", 0, str(e))


async def _log_execution(run_id: str, trigger: str, node: str, status: str,
                         items: int = 0, error: str = ""):
    async with async_session() as db:
        log = ExecutionLog(
            run_id=run_id, trigger=trigger, node_name=node, status=status,
            items_processed=items, error_message=error,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow() if status in ("success", "failed") else None,
        )
        db.add(log)
        await db.commit()


def init_scheduler():
    # Job 1: Collect + Curate + Analyze + Edit (daily at 7:00)
    scheduler.add_job(
        lambda: asyncio.create_task(_run_pipeline("scheduled")),
        CronTrigger.from_crontab(config.CRON_COLLECT),
        id="collect_analyze",
        name="Daily collect & analyze",
    )

    # Job 2: Dispatch (daily at 8:00)
    # In MVP, the whole pipeline runs in Job 1. Job 2 is kept as a
    # placeholder for the separated dispatch phase (future iteration).
    # For now, it just logs a heartbeat.

    logger.info(f"Scheduler initialized: collect={config.CRON_COLLECT}, dispatch={config.CRON_DISPATCH}")
    scheduler.start()
