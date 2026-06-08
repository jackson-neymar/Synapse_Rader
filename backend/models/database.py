import uuid
from datetime import datetime, date

from sqlalchemy import String, Text, Integer, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# 1. RawItem — 采集原始条目
# ---------------------------------------------------------------------------
class RawItem(Base):
    __tablename__ = "raw_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(256), default="")
    raw_tags: Mapped[str] = mapped_column(Text, default="[]")           # JSON string
    stars_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content_snapshot: Mapped[str] = mapped_column(Text, default="{}")   # JSON string

    # Curation state
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True
    )  # pending | curated | filtered_out_keyword | filtered_out_noise
    filter_reason: Mapped[str] = mapped_column(Text, default="")
    category_l1: Mapped[str] = mapped_column(String(64), default="")
    category_l2: Mapped[str] = mapped_column(String(64), default="")
    curated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# 2. AnalyzedItem — LLM 分析结果
# ---------------------------------------------------------------------------
class AnalyzedItem(Base):
    __tablename__ = "analyzed_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    raw_item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("raw_items.id"), unique=True, nullable=False
    )

    summary_one_liner: Mapped[str] = mapped_column(Text, default="")
    summary_highlights: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    summary_comparison: Mapped[str] = mapped_column(Text, default="")
    weight_adjustment: Mapped[str] = mapped_column(String(32), default="")

    # Four-dimensional scores with confidence + reasoning
    score_business: Mapped[int] = mapped_column(Integer, default=0)
    score_business_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    score_business_reason: Mapped[str] = mapped_column(Text, default="")

    score_deploy: Mapped[int] = mapped_column(Integer, default=0)
    score_deploy_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    score_deploy_reason: Mapped[str] = mapped_column(Text, default="")

    score_performance: Mapped[int] = mapped_column(Integer, default=0)
    score_performance_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    score_performance_reason: Mapped[str] = mapped_column(Text, default="")

    score_compatibility: Mapped[int] = mapped_column(Integer, default=0)
    score_compatibility_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    score_compatibility_reason: Mapped[str] = mapped_column(Text, default="")

    score_total: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    confidence_overall: Mapped[float] = mapped_column(Float, default=0.0)
    recommend_level: Mapped[str] = mapped_column(String(32), default="", index=True)

    rag_context_used: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    llm_model_used: Mapped[str] = mapped_column(String(64), default="")

    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# 3. DailyReport — 日报
# ---------------------------------------------------------------------------
class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)

    total_fetched: Mapped[int] = mapped_column(Integer, default=0)
    total_curated: Mapped[int] = mapped_column(Integer, default=0)
    total_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    recommend_high: Mapped[int] = mapped_column(Integer, default=0)
    recommend_mid: Mapped[int] = mapped_column(Integer, default=0)
    recommend_low: Mapped[int] = mapped_column(Integer, default=0)

    report_markdown: Mapped[str] = mapped_column(Text, default="")
    report_status: Mapped[str] = mapped_column(
        String(32), default="complete"
    )  # complete | partial | failed

    feishu_msg_id: Mapped[str] = mapped_column(Text, default="")
    feishu_doc_url: Mapped[str] = mapped_column(Text, default="")
    execution_time_seconds: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# 4. ExecutionLog — 执行日志
# ---------------------------------------------------------------------------
class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), default="scheduled")  # scheduled | manual
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending | running | success | failed

    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Async engine & session
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from settings import config

engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
