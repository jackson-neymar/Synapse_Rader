import hashlib
import logging
from datetime import datetime, timedelta, timezone

import httpx
import feedparser

from settings import config

logger = logging.getLogger(__name__)

TIMEOUT = 30  # seconds per source

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _make_id(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}{title}".encode()).hexdigest()


def _github_headers() -> dict:
    headers = {
        "User-Agent": "Synapse_Rader/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


# ---------------------------------------------------------------------------
# 1. GitHub Trending
# ---------------------------------------------------------------------------
async def fetch_github_trending() -> list[dict]:
    """Fetch NEW AI/ML Python repos created in last 7 days, sorted by stars."""
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    query = f"language:python created:>{week_ago}"
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=30"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, headers=_github_headers())
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"GitHub fetch failed: {e}")
        return []

    items = []
    for repo in data.get("items", []):
        items.append({
            "id": _make_id(repo["html_url"], repo["full_name"]),
            "source": "github",
            "title": repo["full_name"],
            "url": repo["html_url"],
            "description": repo.get("description") or "",
            "author": repo.get("owner", {}).get("login", ""),
            "raw_tags": str(repo.get("topics", [])),
            "stars_count": repo.get("stargazers_count", 0),
        })
    return items


async def fetch_github_trending_daily() -> list[dict]:
    """Fetch NEW repos created yesterday with AI-related topics, sorted by stars."""
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    query = f"created:>{yesterday}"
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=30"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, headers=_github_headers())
            if resp.status_code == 403:
                logger.warning("GitHub API rate limit exceeded")
                return []
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"GitHub daily fetch failed: {e}")
        return []

    items = []
    for repo in data.get("items", []):
        items.append({
            "id": _make_id(repo["html_url"], repo["full_name"]),
            "source": "github",
            "title": repo["full_name"],
            "url": repo["html_url"],
            "description": repo.get("description") or "",
            "author": repo.get("owner", {}).get("login", ""),
            "raw_tags": str(repo.get("topics", [])),
            "stars_count": repo.get("stargazers_count", 0),
        })
    return items


# ---------------------------------------------------------------------------
# 2. HuggingFace
# ---------------------------------------------------------------------------
async def fetch_hf_trending() -> list[dict]:
    """Fetch recently updated models from HuggingFace (via hf-mirror.com)."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                "https://hf-mirror.com/api/models",
                params={"sort": "lastModified", "direction": "-1", "limit": 20},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"HF Mirror fetch failed: {type(e).__name__}: {e}")
        return []
    except Exception as e:
        logger.error(f"HF Mirror unexpected error: {type(e).__name__}: {e}")
        return []

    items = []
    for model in data:
        model_id = model.get("modelId", "") or model.get("id", "")
        items.append({
            "id": _make_id(f"https://huggingface.co/{model_id}", model_id),
            "source": "huggingface",
            "title": model_id,
            "url": f"https://huggingface.co/{model_id}",
            "description": model.get("pipeline_tag") or "",
            "author": model.get("author") or "",
            "raw_tags": str(model.get("tags", [])),
            "stars_count": model.get("downloads") or model.get("likes") or 0,
        })
    return items


# ---------------------------------------------------------------------------
# 3. ModelScope
# ---------------------------------------------------------------------------
async def fetch_hackernews_ai() -> list[dict]:
    """Fetch AI-related stories from Hacker News (via Algolia search API)."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Search HN for AI/ML stories from past week, sorted by points
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": "AI OR LLM OR agent OR machine learning OR open source",
                    "tags": "story",
                    "hitsPerPage": 20,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"HackerNews fetch failed: {e}")
        return []

    items = []
    for hit in data.get("hits", []):
        title = hit.get("title", "") or hit.get("story_title", "")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
        items.append({
            "id": _make_id(url, title),
            "source": "hackernews",
            "title": title,
            "url": url,
            "description": "",
            "author": hit.get("author", ""),
            "raw_tags": str(hit.get("_tags", [])),
            "stars_count": hit.get("points", 0),
        })
    return items


# ---------------------------------------------------------------------------
# 4. arXiv
# ---------------------------------------------------------------------------
def _is_recent(published_str: str, days: int = 3) -> bool:
    """Check if a published date falls within the last N days."""
    try:
        pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        return pub_date >= cutoff
    except (ValueError, IndexError):
        return True  # include if can't parse


async def fetch_arxiv_papers() -> list[dict]:
    """Fetch AI papers from arXiv (cs.AI/CL/CV/LG) posted recently."""
    cats = "cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.CV+OR+cat:cs.LG"
    url = (
        f"https://export.arxiv.org/api/query?search_query={cats}"
        f"&sortBy=submittedDate&sortOrder=descending&start=0&max_results=20"
    )
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"arXiv fetch failed: {e}")
        return []

    feed = feedparser.parse(resp.text)
    items = []
    for entry in feed.entries:
        # Client-side date filter (last 3 days — arXiv doesn't post weekends)
        if not _is_recent(entry.get("published", "")):
            continue

        author = entry.get("author", "")
        items.append({
            "id": _make_id(entry.get("id", ""), entry.get("title", "")),
            "source": "arxiv",
            "title": entry.get("title", "").strip(),
            "url": entry.get("id", ""),
            "description": entry.get("summary", "").strip(),
            "author": author,
            "raw_tags": str([t.get("term", "") for t in entry.get("tags", [])]),
            "stars_count": 0,  # arXiv has no star concept
        })
    return items
