import uuid
from typing import Optional

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    trigger: str               # "scheduled" | "manual"
    current_stage: str          # "collecting" | "curating" | "analyzing" | "editing" | "dispatching"

    # Collector output
    raw_items: list[dict]
    fetch_errors: list[str]

    # Curator output
    curated_items: list[dict]

    # Analyst output
    analyses: list[dict]
    analysis_errors: list[str]

    # Editor output
    report_markdown: str
    report_summary: dict

    # Dispatcher output
    feishu_msg_id: str
    feishu_doc_url: str

    # Flow control
    error: Optional[str]
    status: str                # "running" | "completed" | "partial" | "failed"


def initial_state(trigger: str = "scheduled") -> AgentState:
    return AgentState(
        run_id=uuid.uuid4().hex[:12],
        trigger=trigger,
        current_stage="collecting",
        raw_items=[],
        fetch_errors=[],
        curated_items=[],
        analyses=[],
        analysis_errors=[],
        report_markdown="",
        report_summary={},
        feishu_msg_id="",
        feishu_doc_url="",
        error=None,
        status="running",
    )
