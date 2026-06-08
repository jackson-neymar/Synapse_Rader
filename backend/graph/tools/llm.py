from langchain_openai import ChatOpenAI

from settings import config


def _create_llm(temperature: float, max_tokens: int) -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=config.ANALYSIS_TIMEOUT_SECONDS,
    )


def get_llm() -> ChatOpenAI:
    """通用 LLM 实例（temperature=0.2, max_tokens=4096）"""
    return _create_llm(temperature=0.2, max_tokens=4096)


def get_classification_llm() -> ChatOpenAI:
    """分类/去噪用 LLM（低温度保证一致性，短输出）"""
    return _create_llm(temperature=0.1, max_tokens=1024)


def get_analysis_llm() -> ChatOpenAI:
    """分析/评分用 LLM（中等温度，结构化 JSON 输出）"""
    return _create_llm(temperature=0.2, max_tokens=4096)


def get_editor_llm() -> ChatOpenAI:
    """日报润色用 LLM（稍高温度允许语言多样性）"""
    return _create_llm(temperature=0.4, max_tokens=2048)
