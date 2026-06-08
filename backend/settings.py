import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # DeepSeek LLM
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    # Embedding
    EMBEDDING_BACKEND: str = os.getenv("EMBEDDING_BACKEND", "local")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # GitHub
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # Feishu
    FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "")
    FEISHU_CHAT_ID: str = os.getenv("FEISHU_CHAT_ID", "")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///../data/synapse_rader.db",
    )
    CHROMA_PERSIST_PATH: str = os.getenv("CHROMA_PERSIST_PATH", "../data/chroma")

    # Scheduler
    CRON_COLLECT: str = os.getenv("CRON_COLLECT", "0 7 * * *")
    CRON_DISPATCH: str = os.getenv("CRON_DISPATCH", "0 8 * * *")

    # Config files
    KEYWORDS_CONFIG_PATH: str = os.getenv("KEYWORDS_CONFIG_PATH", "../config/keywords.yaml")

    # Rate limits
    LLM_RATE_LIMIT_RPM: int = int(os.getenv("LLM_RATE_LIMIT_RPM", "30"))
    ANALYSIS_TIMEOUT_SECONDS: int = int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "60"))


config = Config()
