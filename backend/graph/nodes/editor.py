import logging
from datetime import date

from graph.state import AgentState
from graph.tools.llm import get_editor_llm

logger = logging.getLogger(__name__)


def _build_report_summary(state: AgentState) -> dict:
    analyses = state.get("analyses", [])
    return {
        "total_fetched": len(state.get("raw_items", [])),
        "total_curated": len(state.get("curated_items", [])),
        "total_analyzed": len(analyses),
        "recommend_high": sum(1 for a in analyses if a.get("recommend_level") == "强烈推荐"),
        "recommend_mid": sum(1 for a in analyses if a.get("recommend_level") == "值得关注"),
        "recommend_low": sum(1 for a in analyses if a.get("recommend_level") in ("暂不跟进", "不推荐")),
    }


def _build_report_markdown(summary: dict, analyses: list[dict]) -> str:
    today = date.today().strftime("%Y年%m月%d日")
    lines = [
        f"# Synapse_Rader 日报 | {today}",
        "",
        "## 一、今日概览",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 采集条目 | {summary['total_fetched']} |",
        f"| 筛选入库 | {summary['total_curated']} |",
        f"| 强烈推荐 | {summary['recommend_high']} |",
        f"| 值得关注 | {summary['recommend_mid']} |",
        f"| 暂不跟进 | {summary['recommend_low']} |",
        "",
    ]

    # Group by recommend level
    high = [a for a in analyses if a.get("recommend_level") == "强烈推荐"]
    mid = [a for a in analyses if a.get("recommend_level") == "值得关注"]
    low = [a for a in analyses if a.get("recommend_level") in ("暂不跟进", "不推荐")]

    for section_title, items in [("强烈推荐", high), ("值得关注", mid)]:
        if not items:
            continue
        lines.append(f"## {['二','三'][['强烈推荐','值得关注'].index(section_title)]}、{section_title}（≥{ '4.0' if section_title=='强烈推荐' else '3.0'}分）")
        lines.append("")
        for item in items:
            scores = item.get("scores", {})
            title = item.get('title', '') or item.get('raw_item_id', '?')[:20]
            lines.append(f"### [{item.get('category_l1', '?')}] {title[:60]} | 评分：{item.get('score_total', 0):.1f} — {item.get('recommend_level', '?')}")
            lines.append(f"- **一句话总结**：{item.get('summary_one_liner', '')}")
            highlights = item.get("summary_highlights", [])
            if isinstance(highlights, str):
                try:
                    import json
                    highlights = json.loads(highlights)
                except Exception:
                    highlights = []
            if highlights:
                lines.append("- **核心亮点**：")
                for h in highlights:
                    lines.append(f"  - {h}")
            lines.append("- **评分明细**：")
            lines.append(f"  | 维度 | 分数 | 置信度 | 理由 |")
            lines.append(f"  |------|------|--------|------|")
            for dim, label in [("business", "商业潜力"), ("deploy", "落地难度"), ("performance", "性能指标"), ("compatibility", "业务兼容性")]:
                s = scores.get(dim, {})
                conf = s.get("confidence", 0)
                warn = " ⚠️" if conf < 0.6 else ""
                lines.append(f"  | {label} | {s.get('value', '?')} | {int(conf*100)}%{warn} | {s.get('reason', '')[:40]} |")
            lines.append(f"- **链接**：{item.get('url', '')}")
            lines.append("")

    if low:
        lines.append(f"## 四、暂不跟进")
        lines.append(f"| 标题 | 分类 | 评分 | 理由 |")
        lines.append(f"|------|------|------|------|")
        for item in low:
            scores = item.get("scores", {})
            reason = ""
            for dim in scores.values():
                if dim.get("reason"):
                    reason = dim["reason"][:20]
                    break
            lines.append(f"| {item.get('title', '?')[:40]} | {item.get('category_l1', '?')} | {item.get('score_total', 0):.1f} | {reason} |")
        lines.append("")

    lines.append("---")
    lines.append("*本报告由 Synapse_Rader 多智能体系统自动生成*")

    return "\n".join(lines)


async def editor_node(state: AgentState) -> AgentState:
    analyses = state.get("analyses", [])
    logger.info(f"Editor start: {len(analyses)} analyses")

    summary = _build_report_summary(state)
    markdown = _build_report_markdown(summary, analyses)

    logger.info(
        f"Editor done: fetched={summary['total_fetched']}, "
        f"curated={summary['total_curated']}, "
        f"high={summary['recommend_high']}, mid={summary['recommend_mid']}"
    )

    return {
        "report_markdown": markdown,
        "report_summary": summary,
        "current_stage": "dispatching",
    }
