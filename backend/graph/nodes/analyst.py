import asyncio
import json
import logging
import re

import numpy as np

from graph.state import AgentState
from graph.tools.llm import get_analysis_llm
from graph.tools.rag import hybrid_search, index_analyzed_item
from graph.tools.prompts import build_analysis_prompt
from settings import config


def _to_native(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_native(i) for i in obj]
    return obj

logger = logging.getLogger(__name__)


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"```json\s*|```\s*", "", text)
    text = text.replace("'", '"').replace("'", "'").replace("'", "'")
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


async def analyze_single_item(item: dict) -> dict:
    """Analyze one intelligence item: RAG → LLM → index → result."""
    try:
        # Step 1: RAG search
        query = f"{item.get('title', '')} {item.get('description', '')}"
        rag_results = hybrid_search(query, n_results=5)
    except Exception as e:
        logger.warning(f"RAG search failed for {item.get('id', '?')}: {e}")
        rag_results = []

    try:
        # Step 2: Build prompt & call LLM
        prompt = build_analysis_prompt(item, rag_results)
        llm = get_analysis_llm()
        resp = await llm.ainvoke(prompt)
        analysis = extract_json(resp.content)
    except Exception as e:
        logger.warning(f"LLM analysis failed for {item.get('id', '?')}: {e}")
        return {
            "id": item.get("id", ""),
            "raw_item_id": item.get("id", ""),
            "summary_one_liner": "",
            "summary_highlights": [],
            "score_total": 0,
            "confidence_overall": 0,
            "recommend_level": "error",
            "error": str(e),
        }

    # Step 3: Enrich with item metadata
    analysis["id"] = item.get("id", "")
    analysis["raw_item_id"] = item.get("id", "")
    analysis["title"] = item.get("title", "")
    analysis["url"] = item.get("url", "")
    analysis["category_l1"] = item.get("category_l1", "")
    analysis["category_l2"] = item.get("category_l2", "")
    analysis["source"] = item.get("source", "")
    analysis["rag_context_used"] = [
        {"id": r["id"], "similarity": r["similarity"], "title": r["metadata"].get("title", "")}
        for r in rag_results
    ]

    # Step 4: Index into ChromaDB (fire and forget)
    try:
        index_data = {
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "category_l1": item.get("category_l1", ""),
            "category_l2": item.get("category_l2", ""),
            "summary_one_liner": analysis.get("summary_one_liner", ""),
            "summary_highlights": analysis.get("summary_highlights", []),
            "score_total": analysis.get("score_total", 0),
            "recommend_level": analysis.get("recommend_level", ""),
            "rag_context_used": analysis.get("rag_context_used", []),
        }
        index_analyzed_item(index_data)
    except Exception as e:
        logger.warning(f"ChromaDB index failed: {e}")

    return _to_native(analysis)


async def analyst_node(state: AgentState) -> AgentState:
    """Analyze all curated items in parallel (8 concurrency)."""
    curated = state.get("curated_items", [])
    if not curated:
        logger.warning("No curated items to analyze")
        return {"current_stage": "editing", "analyses": [], "analysis_errors": []}

    logger.info(f"Analyst start: {len(curated)} items")

    # Parallel analysis with semaphore for rate limiting
    sem = asyncio.Semaphore(8)
    async def analyze_one(item):
        async with sem:
            return await analyze_single_item(item)

    results = await asyncio.gather(*[analyze_one(item) for item in curated])

    analyses = []
    errors = []
    for r in results:
        if r.get("recommend_level") == "error":
            errors.append(r)
        else:
            analyses.append(r)

    # Sort by score descending
    analyses.sort(key=lambda x: x.get("score_total", 0), reverse=True)

    # Persist to DB
    await _save_analyses_to_db(analyses)

    logger.info(f"Analyst done: {len(analyses)} analyzed, {len(errors)} errors")
    return {
        "analyses": analyses,
        "analysis_errors": [e.get("error", "unknown") for e in errors],
        "current_stage": "editing",
    }


async def _save_analyses_to_db(analyses: list[dict]):
    """Persist analyzed items to the analyzed_items table (upsert by raw_item_id)."""
    from models.database import async_session, AnalyzedItem
    from sqlalchemy import select as sa_select
    from datetime import datetime

    async with async_session() as db:
        inserted = 0
        updated = 0
        for a in analyses:
            rid = a.get("raw_item_id", "")
            existing = (await db.execute(
                sa_select(AnalyzedItem).where(AnalyzedItem.raw_item_id == rid)
            )).scalar_one_or_none()

            scores = a.get("scores", {})
            kwargs = dict(
                summary_one_liner=a.get("summary_one_liner", ""),
                summary_highlights=str(a.get("summary_highlights", [])),
                summary_comparison=a.get("summary_comparison", ""),
                weight_adjustment=a.get("weight_adjustment", ""),
                score_business=scores.get("business", {}).get("value", 0),
                score_business_confidence=scores.get("business", {}).get("confidence", 0),
                score_business_reason=scores.get("business", {}).get("reason", ""),
                score_deploy=scores.get("deploy", {}).get("value", 0),
                score_deploy_confidence=scores.get("deploy", {}).get("confidence", 0),
                score_deploy_reason=scores.get("deploy", {}).get("reason", ""),
                score_performance=scores.get("performance", {}).get("value", 0),
                score_performance_confidence=scores.get("performance", {}).get("confidence", 0),
                score_performance_reason=scores.get("performance", {}).get("reason", ""),
                score_compatibility=scores.get("compatibility", {}).get("value", 0),
                score_compatibility_confidence=scores.get("compatibility", {}).get("confidence", 0),
                score_compatibility_reason=scores.get("compatibility", {}).get("reason", ""),
                score_total=a.get("score_total", 0),
                confidence_overall=a.get("confidence_overall", 0),
                recommend_level=a.get("recommend_level", ""),
                rag_context_used=str(a.get("rag_context_used", [])),
                llm_model_used="deepseek-chat",
                analyzed_at=datetime.utcnow(),
            )

            if existing:
                for k, v in kwargs.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.add(AnalyzedItem(id=a.get("id", ""), raw_item_id=rid, **kwargs))
                inserted += 1
        await db.commit()
    logger.info(f"Saved analyzed_items: {inserted} new, {updated} updated")
