from datetime import date, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from models.database import async_session, DailyReport, AnalyzedItem

router = APIRouter()


@router.get("/stats")
async def get_stats(days: int = Query(7, ge=1, le=30)):
    """Get daily stats for the past N days."""
    result = []
    for i in range(days):
        d = date.today() - timedelta(days=i)
        async with async_session() as db:
            rep = (await db.execute(
                select(DailyReport).where(DailyReport.report_date == d)
            )).scalar_one_or_none()

            result.append({
                "date": str(d),
                "total_fetched": rep.total_fetched if rep else 0,
                "total_analyzed": rep.total_analyzed if rep else 0,
                "recommend_high": rep.recommend_high if rep else 0,
            })

    return {"stats": result}
