from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import select, func, and_

from models.database import async_session, AnalyzedItem, RawItem

router = APIRouter()


@router.get("/items")
async def search_items(
    date_from: str | None = Query(None, description="Start date (YYYY-MM-DD), defaults to today"),
    date_to: str | None = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
    recommend_level: str | None = Query(None, description="强烈推荐 / 值得关注 / 暂不跟进 / 不推荐"),
    score_min: float | None = Query(None, description="Minimum score"),
    score_max: float | None = Query(None, description="Maximum score"),
    keyword: str | None = Query(None, description="Search in summary fields"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort_by: str = Query("score_total", description="score_total / analyzed_at"),
    sort_order: str = Query("desc", description="asc / desc"),
):
    today = date.today().isoformat()
    d_from = f"{date_from} 00:00:00" if date_from else f"{today} 00:00:00"
    d_to = f"{date_to} 23:59:59" if date_to else f"{today} 23:59:59"

    async with async_session() as db:
        stmt = select(AnalyzedItem)

        conditions = [
            AnalyzedItem.analyzed_at >= d_from,
            AnalyzedItem.analyzed_at <= d_to,
        ]
        if recommend_level:
            conditions.append(AnalyzedItem.recommend_level == recommend_level)
        if score_min is not None:
            conditions.append(AnalyzedItem.score_total >= score_min)
        if score_max is not None:
            conditions.append(AnalyzedItem.score_total <= score_max)
        if keyword:
            conditions.append(AnalyzedItem.summary_one_liner.contains(keyword))

        stmt = stmt.where(and_(*conditions))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Sort
        sort_col = AnalyzedItem.score_total if sort_by == "score_total" else AnalyzedItem.analyzed_at
        stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        # Dedup + paginate
        stmt = stmt.order_by(AnalyzedItem.analyzed_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()

        # Dedup by raw_item_id (keep highest score)
        seen = {}
        for item in items:
            if item.raw_item_id not in seen or item.score_total > seen[item.raw_item_id].score_total:
                seen[item.raw_item_id] = item
        items = list(seen.values())

        # Resolve titles from raw_items
        raw_ids = [item.raw_item_id for item in items]
        title_map = {}
        if raw_ids:
            raws = (await db.execute(
                select(RawItem).where(RawItem.id.in_(raw_ids))
            )).scalars().all()
            title_map = {r.id: r.title for r in raws}

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "items": [
                {
                    "id": item.id,
                    "title": title_map.get(item.raw_item_id, item.raw_item_id),
                    "url": "",  # Available from raw_item join if needed
                    "source": "",
                    "category_l1": "",
                    "summary_one_liner": item.summary_one_liner,
                    "summary_highlights": item.summary_highlights,
                    "score_total": item.score_total,
                    "confidence_overall": item.confidence_overall,
                    "recommend_level": item.recommend_level,
                    "analyzed_at": str(item.analyzed_at) if item.analyzed_at else None,
                    "scores": {
                        "business": {"value": item.score_business, "confidence": item.score_business_confidence, "reason": item.score_business_reason},
                        "deploy": {"value": item.score_deploy, "confidence": item.score_deploy_confidence, "reason": item.score_deploy_reason},
                        "performance": {"value": item.score_performance, "confidence": item.score_performance_confidence, "reason": item.score_performance_reason},
                        "compatibility": {"value": item.score_compatibility, "confidence": item.score_compatibility_confidence, "reason": item.score_compatibility_reason},
                    },
                }
                for item in items
            ],
        }
