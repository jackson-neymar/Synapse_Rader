import logging
from datetime import date

import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
from lark_oapi.api.docx.v1 import CreateDocumentRequest, CreateDocumentRequestBody

from settings import config

logger = logging.getLogger(__name__)

FEISHU_MSG_MAX_BYTES = 10240  # 10KB limit


def _get_client() -> lark.Client | None:
    if not config.FEISHU_APP_ID or not config.FEISHU_APP_SECRET:
        logger.warning("Feishu credentials not configured, skipping push")
        return None
    return lark.Client.builder() \
        .app_id(config.FEISHU_APP_ID) \
        .app_secret(config.FEISHU_APP_SECRET) \
        .build()


def build_feishu_message(report_summary: dict, report_markdown: str) -> str:
    """Build a compact Feishu card message (≤10KB) from the daily report."""
    today = date.today().strftime("%Y年%m月%d日")
    lines = [
        f"☕ Synapse_Rader 日报 | {today}",
        "",
        f"📊 采集 {report_summary.get('total_fetched', 0)} 条 | "
        f"筛选入库 {report_summary.get('total_curated', 0)} 条 | "
        f"强烈推荐 {report_summary.get('recommend_high', 0)} 条 | "
        f"值得关注 {report_summary.get('recommend_mid', 0)} 条",
        "",
        "═══════════════════════════",
        "🔴 强烈推荐",
        "",
    ]

    # Extract "强烈推荐" items from markdown
    import re
    high_section = False
    count = 0
    for line in report_markdown.split("\n"):
        if "强烈推荐" in line and "##" in line:
            high_section = True
            continue
        if high_section:
            if line.startswith("###"):
                count += 1
                if count > 3:  # Max 3 items in message
                    break
                lines.append(line.replace("### ", f"{count}. "))
            elif line.startswith("- **一句话总结**"):
                lines.append(f"   {line.replace('- **一句话总结**：', '')}")
            elif "**链接**" in line:
                link = line.replace("- **链接**：", "").strip()
                if link:
                    lines.append(f"   🔗 {link[:80]}")

    if count == 0:
        lines.append("（今日无强烈推荐条目）")

    lines.append("═══════════════════════════")
    lines.append("📄 完整报告：见飞书文档")

    msg = "\n".join(lines)
    if len(msg.encode()) > FEISHU_MSG_MAX_BYTES:
        # Truncate to safe size
        while len(msg.encode()) > FEISHU_MSG_MAX_BYTES - 100:
            lines.pop()
        lines.append("... (内容过长已截断)")
        lines.append("═══════════════════════════")
        msg = "\n".join(lines)

    return msg


def send_feishu_group_message(message: str) -> str:
    """Send message to Feishu group. Returns message_id or empty string."""
    client = _get_client()
    if client is None:
        return ""

    try:
        req = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(config.FEISHU_CHAT_ID)
                .msg_type("text")
                .content(f'{{"text":"{message}"}}')
                .build()) \
            .build()
        resp = client.im.v1.message.create(req)
        if resp.success():
            msg_id = resp.data.message_id or ""
            logger.info(f"Feishu message sent: {msg_id}")
            return msg_id
        else:
            logger.error(f"Feishu message failed: {resp.code} {resp.msg}")
            return ""
    except Exception as e:
        logger.error(f"Feishu message exception: {e}")
        return ""


def create_feishu_doc(title: str, content: str) -> str:
    """Create a Feishu doc. Returns doc_url or empty string."""
    client = _get_client()
    if client is None:
        return ""

    try:
        req = CreateDocumentRequest.builder() \
            .request_body(CreateDocumentRequestBody.builder()
                .title(title)
                .build()) \
            .build()
        resp = client.docx.v1.document.create(req)
        if resp.success():
            doc_id = resp.data.document.document_id or ""
            doc_url = f"https://{config.FEISHU_APP_ID.split('_')[0] if config.FEISHU_APP_ID else 'internal'}.feishu.cn/docx/{doc_id}"
            logger.info(f"Feishu doc created: {doc_url}")
            return doc_url
        else:
            logger.error(f"Feishu doc failed: {resp.code} {resp.msg}")
            return ""
    except Exception as e:
        logger.error(f"Feishu doc exception: {e}")
        return ""
