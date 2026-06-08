import hashlib
import logging
from datetime import datetime

from sqlalchemy import select

from models.database import async_session, RawItem

logger = logging.getLogger(__name__)


def deduplicate_items(items: list[dict]) -> list[dict]:
    """Deduplicate by SHA256(url + title). Keeps first occurrence."""
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        item_id = item.get("id") or hashlib.sha256(
            f"{item['url']}{item['title']}".encode()
        ).hexdigest()
        if item_id not in seen:
            item["id"] = item_id
            seen.add(item_id)
            result.append(item)
    return result


async def bulk_insert_raw_items(items: list[dict]) -> int:
    """INSERT OR IGNORE raw items. Returns count of newly inserted rows."""
    if not items:
        return 0

    inserted = 0
    async with async_session() as db:
        for item in items:
            existing = await db.get(RawItem, item["id"])
            if existing is None:
                db.add(RawItem(
                    id=item["id"],
                    source=item.get("source", ""),
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    author=item.get("author", ""),
                    raw_tags=item.get("raw_tags", "[]"),
                    stars_count=item.get("stars_count", 0),
                    fetched_at=datetime.utcnow(),
                    status="pending",
                ))
                inserted += 1
        await db.commit()
    return inserted


async def get_pending_items() -> list[RawItem]:
    """Return all raw_items with status='pending', ordered by created_at ASC."""
    async with async_session() as db:
        result = await db.execute(
            select(RawItem)
            .where(RawItem.status == "pending")
            .order_by(RawItem.created_at.asc())
        )
        return list(result.scalars().all())


async def batch_update_item_status(item_ids: list[str], status: str, reason: str = "") -> None:
    """Batch update status and filter_reason for given item IDs."""
    if not item_ids:
        return
    async with async_session() as db:
        for item_id in item_ids:
            item = await db.get(RawItem, item_id)
            if item:
                item.status = status
                item.filter_reason = reason
        await db.commit()
