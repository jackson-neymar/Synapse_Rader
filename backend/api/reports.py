from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from models.database import async_session, DailyReport, AnalyzedItem

router = APIRouter()


@router.get("/report/today")
async def get_today_report():
    """Get today's daily report with analyzed items."""
    async with async_session() as db:
        rep = (await db.execute(
            select(DailyReport)
            .where(DailyReport.report_date == date.today())
            .order_by(DailyReport.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        if rep is None:
            return {"report_summary": None, "report_markdown": "", "items": []}

        today_str = f"{date.today().isoformat()} 00:00:00"
        items = (await db.execute(
            select(AnalyzedItem)
            .where(AnalyzedItem.analyzed_at >= today_str)
            .order_by(AnalyzedItem.score_total.desc())
        )).scalars().all()
        raw_ids = [item.raw_item_id for item in items]
        title_map = {}
        url_map = {}
        if raw_ids:
            from models.database import RawItem
            raws = (await db.execute(
                select(RawItem).where(RawItem.id.in_(raw_ids))
            )).scalars().all()
            title_map = {r.id: r.title for r in raws}
            url_map = {r.id: r.url for r in raws}

        return {
            "report_summary": {
                "total_fetched": rep.total_fetched,
                "total_curated": rep.total_curated,
                "total_analyzed": rep.total_analyzed,
                "recommend_high": rep.recommend_high,
                "recommend_mid": rep.recommend_mid,
                "recommend_low": rep.recommend_low,
                "execution_time_seconds": rep.execution_time_seconds,
            },
            "report_markdown": rep.report_markdown,
            "report_status": rep.report_status,
            "items": [_analyzed_to_dict(item, title_map, url_map) for item in items],
        }


@router.get("/report/{report_date}")
async def get_report_by_date(report_date: str):
    async with async_session() as db:
        rep = (await db.execute(
            select(DailyReport).where(DailyReport.report_date == report_date)
        )).scalar_one_or_none()
        if rep is None:
            raise HTTPException(status_code=404, detail="Report not found")
        return {
            "report_summary": {
                "total_fetched": rep.total_fetched,
                "total_curated": rep.total_curated,
                "total_analyzed": rep.total_analyzed,
                "recommend_high": rep.recommend_high,
                "recommend_mid": rep.recommend_mid,
                "recommend_low": rep.recommend_low,
            },
            "report_markdown": rep.report_markdown,
            "report_status": rep.report_status,
        }


def _analyzed_to_dict(item: AnalyzedItem, title_map: dict | None = None, url_map: dict | None = None) -> dict:
    title_map = title_map or {}
    url_map = url_map or {}
    return {
        "id": item.id,
        "title": title_map.get(item.raw_item_id, item.raw_item_id),
        "url": url_map.get(item.raw_item_id, ""),
        "raw_item_id": item.raw_item_id,
        "summary_one_liner": item.summary_one_liner,
        "summary_highlights": item.summary_highlights,
        "summary_comparison": item.summary_comparison,
        "scores": {
            "business": {"value": item.score_business, "confidence": item.score_business_confidence, "reason": item.score_business_reason},
            "deploy": {"value": item.score_deploy, "confidence": item.score_deploy_confidence, "reason": item.score_deploy_reason},
            "performance": {"value": item.score_performance, "confidence": item.score_performance_confidence, "reason": item.score_performance_reason},
            "compatibility": {"value": item.score_compatibility, "confidence": item.score_compatibility_confidence, "reason": item.score_compatibility_reason},
        },
        "score_total": item.score_total,
        "confidence_overall": item.confidence_overall,
        "recommend_level": item.recommend_level,
        "analyzed_at": str(item.analyzed_at) if item.analyzed_at else None,
    }
