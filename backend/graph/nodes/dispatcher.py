import logging
from datetime import date

from sqlalchemy import select

from graph.state import AgentState
from graph.tools.feishu import build_feishu_message, send_feishu_group_message, create_feishu_doc
from models.database import async_session, DailyReport

logger = logging.getLogger(__name__)


async def _save_report_to_db(state: AgentState) -> str:
    """Persist daily report to database (upsert by date)."""
    summary = state.get("report_summary", {})
    async with async_session() as db:
        existing = (await db.execute(
            select(DailyReport).where(DailyReport.report_date == date.today())
        )).scalar_one_or_none()

        if existing:
            existing.run_id = state.get("run_id", "")
            existing.total_fetched = summary.get("total_fetched", 0)
            existing.total_curated = summary.get("total_curated", 0)
            existing.total_analyzed = summary.get("total_analyzed", 0)
            existing.recommend_high = summary.get("recommend_high", 0)
            existing.recommend_mid = summary.get("recommend_mid", 0)
            existing.recommend_low = summary.get("recommend_low", 0)
            existing.report_markdown = state.get("report_markdown", "")
            existing.report_status = state.get("status", "complete")
            await db.commit()
            return existing.id
        else:
            report = DailyReport(
                report_date=date.today(),
                run_id=state.get("run_id", ""),
                total_fetched=summary.get("total_fetched", 0),
                total_curated=summary.get("total_curated", 0),
                total_analyzed=summary.get("total_analyzed", 0),
                recommend_high=summary.get("recommend_high", 0),
                recommend_mid=summary.get("recommend_mid", 0),
                recommend_low=summary.get("recommend_low", 0),
                report_markdown=state.get("report_markdown", ""),
                report_status=state.get("status", "complete"),
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)
            return report.id


async def dispatcher_node(state: AgentState) -> AgentState:
    """Push report to Feishu and save to DB."""

    # Save to DB first (always works, no external dependency)
    report_id = await _save_report_to_db(state)
    logger.info(f"Report saved to DB: {report_id}")

    # Build Feishu message
    summary = state.get("report_summary", {})
    markdown = state.get("report_markdown", "")
    msg = build_feishu_message(summary, markdown)

    # Send Feishu group message (gracefully skip if not configured)
    msg_id = send_feishu_group_message(msg)

    # Create Feishu doc
    doc_title = f"Synapse_Rader 日报 | {date.today().strftime('%Y-%m-%d')}"
    doc_url = create_feishu_doc(doc_title, markdown)

    # Update DB with Feishu info
    if msg_id or doc_url:
        async with async_session() as db:
            rep = await db.get(DailyReport, report_id)
            if rep:
                rep.feishu_msg_id = msg_id or ""
                rep.feishu_doc_url = doc_url or ""
                await db.commit()

    return {
        "feishu_msg_id": msg_id,
        "feishu_doc_url": doc_url,
        "current_stage": "completed",
        "status": "completed",
    }
