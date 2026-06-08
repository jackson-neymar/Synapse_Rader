import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from graph import build_synapse_rader_graph, initial_state
from models.database import async_session, ExecutionLog

logger = logging.getLogger(__name__)
router = APIRouter()

_running_lock = asyncio.Lock()
_current_run_id: str | None = None


@router.post("/trigger/daily-run")
async def trigger_daily_run():
    global _current_run_id

    if _running_lock.locked():
        raise HTTPException(status_code=409, detail="已有运行中的流程，请等待完成")

    run_id = uuid.uuid4().hex[:12]
    _current_run_id = run_id

    # Schedule in background thread
    async def run_pipeline():
        async with _running_lock:
            try:
                graph = build_synapse_rader_graph()
                state = initial_state(trigger="manual")
                config = {"configurable": {"thread_id": run_id}}

                # Log start
                await _log_node(run_id, "pipeline", "running", 0)

                result = await graph.ainvoke(state, config)

                # Log completion
                await _log_node(run_id, "pipeline", "success",
                                len(result.get("raw_items", [])))
                logger.info(f"Pipeline {run_id} completed")
            except Exception as e:
                logger.error(f"Pipeline {run_id} failed: {e}")
                await _log_node(run_id, "pipeline", "failed", 0, str(e))

    asyncio.create_task(run_pipeline())

    return {
        "run_id": run_id,
        "status": "started",
        "message": "日报流程已启动，预计 1-3 分钟完成",
    }


@router.get("/run-status/{run_id}")
async def get_run_status(run_id: str):
    async with async_session() as db:
        logs = (await db.execute(
            select(ExecutionLog).where(ExecutionLog.run_id == run_id)
        )).scalars().all()

        nodes = []
        overall = "pending"
        for log in logs:
            nodes.append({
                "name": log.node_name,
                "status": log.status,
                "items_processed": log.items_processed,
                "error": log.error_message or None,
                "started_at": str(log.started_at) if log.started_at else None,
                "finished_at": str(log.finished_at) if log.finished_at else None,
            })
            if log.status == "failed":
                overall = "failed"
            elif log.status == "success" and overall != "failed":
                overall = "success"
            elif log.status == "running":
                overall = "running"

        return {
            "run_id": run_id,
            "overall_status": overall,
            "nodes": nodes,
        }


@router.get("/run-history")
async def get_run_history(page: int = 1, page_size: int = 20):
    async with async_session() as db:
        stmt = (
            select(ExecutionLog)
            .order_by(ExecutionLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        logs = (await db.execute(stmt)).scalars().all()

        # Group by run_id
        runs = {}
        for log in logs:
            if log.run_id not in runs:
                runs[log.run_id] = {
                    "run_id": log.run_id,
                    "trigger": log.trigger,
                    "started_at": str(log.started_at) if log.started_at else None,
                    "nodes": {},
                }
            runs[log.run_id]["nodes"][log.node_name] = log.status

        return {"runs": list(runs.values()), "page": page, "page_size": page_size}


async def _log_node(run_id: str, node_name: str, status: str, items: int, error: str = ""):
    async with async_session() as db:
        log = ExecutionLog(
            run_id=run_id,
            trigger="manual",
            node_name=node_name,
            status=status,
            items_processed=items,
            error_message=error,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow() if status in ("success", "failed") else None,
        )
        db.add(log)
        await db.commit()
