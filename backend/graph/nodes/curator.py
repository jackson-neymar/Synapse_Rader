import json
import logging
import re

from config import read_keywords
from graph.state import AgentState
from graph.tools.llm import get_classification_llm
from graph.tools.storage import batch_update_item_status

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# L1: Keyword filter
# ---------------------------------------------------------------------------
def _match_keywords(text: str, keywords: list[str]) -> bool:
    """Check if text contains any keyword (case-insensitive EN, substring ZH)."""
    text_lower = text.lower()
    for kw in keywords:
        if kw.isascii():
            if kw.lower() in text_lower:
                return True
        else:
            if kw in text:
                return True
    return False


def keyword_filter(items: list[dict], keywords: list[str]) -> tuple[list[dict], list[str]]:
    """Filter items by L1 keyword matching. Returns (passed, rejected_ids)."""
    passed: list[dict] = []
    rejected: list[str] = []

    for item in items:
        search_text = f"{item.get('title', '')} {item.get('description', '')}"
        if _match_keywords(search_text, keywords):
            passed.append(item)
        else:
            rejected.append(item.get("id", ""))

    return passed, rejected


# ---------------------------------------------------------------------------
# L2: LLM classification
# ---------------------------------------------------------------------------
async def llm_batch_classify(items: list[dict]) -> tuple[list[dict], list[str]]:
    """LLM classifies each item into domain + sub-tag. Returns (passed, rejected_ids)."""
    if not items:
        return [], []

    # Build a compact input for the LLM
    item_list = []
    for item in items:
        item_list.append({
            "id": item["id"],
            "title": item.get("title", "")[:200],
            "description": item.get("description", "")[:300],
        })

    prompt = f"""你是一个AI技术情报分类专家。对以下{len(item_list)}条内容逐一判断：

1. 是否属于以下三个领域之一：AI Agent / 多模态大模型 / NLP
2. 打二级标签：新模型发布 / 论文 / 开源工具/框架 / 技术路线/观点 / 数据集 / 产品动态

输出严格JSON数组，每个元素格式：
{{"id": "...", "category_l1": "AI Agent/多模态大模型/NLP/其他", "category_l2": "...", "is_relevant": true/false}}

待分类内容：
{json.dumps(item_list, ensure_ascii=False, indent=2)}"""

    llm = get_classification_llm()
    resp = await llm.ainvoke(prompt)
    text = resp.content.strip()
    # Extract JSON array
    text = re.sub(r"```json\s*|```\s*", "", text)
    text = text.replace("'", '"')
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    try:
        classifications = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"L2 classification JSON parse failed, passing all items")
        return items, []

    passed: list[dict] = []
    rejected: list[str] = []

    # Build lookup from items by id
    item_map = {item["id"]: item for item in items}

    for cls in classifications:
        item_id = cls.get("id", "")
        item = item_map.get(item_id)
        if item is None:
            continue

        if cls.get("is_relevant", True):
            item["category_l1"] = cls.get("category_l1", "")
            item["category_l2"] = cls.get("category_l2", "")
            passed.append(item)
        else:
            rejected.append(item_id)

    return passed, rejected


# ---------------------------------------------------------------------------
# L3: LLM denoising
# ---------------------------------------------------------------------------
async def llm_batch_denoise(items: list[dict]) -> tuple[list[dict], list[str]]:
    """LLM removes spam/marketing/noise. Returns (passed, rejected_ids)."""
    if not items:
        return [], []

    item_list = []
    for item in items:
        item_list.append({
            "id": item["id"],
            "title": item.get("title", "")[:200],
            "description": item.get("description", "")[:300],
        })

    prompt = f"""你是一个内容质量审核专家。判断以下{len(item_list)}条内容是否为灌水/营销/无关噪声。

灌水/噪声特征：无具体技术内容、纯推广文案、重复率高、摘要空洞、与AI技术无关。

输出严格JSON数组：
[{{"id": "...", "is_noise": true/false, "reason": "..."}}]

待审核内容：
{json.dumps(item_list, ensure_ascii=False, indent=2)}"""

    llm = get_classification_llm()
    resp = await llm.ainvoke(prompt)
    text = resp.content.strip()
    text = re.sub(r"```json\s*|```\s*", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    try:
        results = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"L3 denoise JSON parse failed, passing all items")
        return items, []

    passed: list[dict] = []
    rejected: list[str] = []

    item_map = {item["id"]: item for item in items}

    for r in results:
        item_id = r.get("id", "")
        if item_id not in item_map:
            continue
        if r.get("is_noise", False):
            rejected.append(item_id)
        else:
            passed.append(item_map[item_id])

    return passed, rejected


# ---------------------------------------------------------------------------
# Curator Node: L1 → L2 → L3 pipeline (step 2.9)
# ---------------------------------------------------------------------------
async def curator_node(state: AgentState) -> AgentState:
    keywords = read_keywords()
    raw_items = state.get("raw_items", [])
    logger.info(f"Curator start: {len(raw_items)} raw items")

    # L1 — keyword filter (rule-based, fast)
    l1_passed, l1_rejected = keyword_filter(raw_items, keywords)
    logger.info(f"L1: {len(l1_passed)} passed, {len(l1_rejected)} rejected")
    await batch_update_item_status(l1_rejected, "filtered_out_keyword", "L1: no keyword match")

    # L2 — LLM classify
    l2_passed, l2_rejected = await llm_batch_classify(l1_passed)
    logger.info(f"L2: {len(l2_passed)} passed, {len(l2_rejected)} rejected")
    await batch_update_item_status(l2_rejected, "filtered_out_noise", "L2: not in target domains")

    # L3 — LLM denoise
    l3_passed, l3_rejected = await llm_batch_denoise(l2_passed)
    logger.info(f"L3: {len(l3_passed)} passed, {len(l3_rejected)} rejected")
    await batch_update_item_status(l3_rejected, "filtered_out_noise", "L3: noise/spam")

    return {
        "curated_items": l3_passed,
        "current_stage": "analyzing",
    }
