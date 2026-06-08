import asyncio
import logging

from graph.state import AgentState
from graph.tools.fetchers import (
    fetch_github_trending,
    fetch_github_trending_daily,
    fetch_hf_trending,
    fetch_hackernews_ai,
    fetch_arxiv_papers,
)
from graph.tools.storage import deduplicate_items, bulk_insert_raw_items

logger = logging.getLogger(__name__)


async def collector_node(state: AgentState) -> AgentState:
    """Run 4 source fetchers in parallel, deduplicate, and store to raw_items."""

    # Parallel fetch (asyncio.gather — all fetchers are async httpx calls)
    results = await asyncio.gather(
        fetch_github_trending(),
        fetch_github_trending_daily(),
        fetch_hf_trending(),
        fetch_hackernews_ai(),
        fetch_arxiv_papers(),
        return_exceptions=True,
    )

    fetcher_names = [
        "github_trending",
        "github_daily",
        "huggingface",
        "hackernews",
        "arxiv",
    ]

    all_items: list[dict] = []
    fetch_errors: list[str] = []

    for name, result in zip(fetcher_names, results):
        if isinstance(result, Exception):
            err_msg = f"{name}: {type(result).__name__}: {result}"
            logger.error(err_msg)
            fetch_errors.append(err_msg)
        elif isinstance(result, list):
            all_items.extend(result)
        else:
            logger.warning(f"{name}: unexpected return type {type(result)}")

    # Deduplicate
    unique_items = deduplicate_items(all_items)
    logger.info(
        f"Collected {len(all_items)} items, {len(unique_items)} after dedup"
    )

    # Store
    inserted = await bulk_insert_raw_items(unique_items)
    logger.info(f"Inserted {inserted} new raw_items (skipped {len(unique_items) - inserted} duplicates)")

    return {
        "raw_items": unique_items,
        "fetch_errors": fetch_errors,
        "current_stage": "curating",
    }
