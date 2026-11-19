from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ..core.config import settings


class Base(DeclarativeBase):
    pass


class Report(Base):
    """评估报告主表：report_id、企业名、画像快照与 summary/report_md 两份 JSON/Markdown。"""
    __tablename__ = "reports"
    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), index=True)
    life_stage: Mapped[str] = mapped_column(String(16))
    llm_mode: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    summary_json: Mapped[str] = mapped_column(Text)
    report_md: Mapped[str] = mapped_column(Text, default="")


class FindingRow(Base):
    """风险发现明细：每行一条发现单的完整 JSON（与报告 summary 分开存，便于台账 diff）。"""
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), ForeignKey("reports.report_id"), index=True)
    finding_json: Mapped[str] = mapped_column(Text)


class JobRow(Base):
    """异步评估任务的进度落库（内存 JOBS 的持久化镜像，仅查询服务重启前的记录）。"""
    __tablename__ = "jobs"
    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    stage: Mapped[str] = mapped_column(String(64), default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    report_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceRow(Base):
    """知识库来源登记：原文存储路径、sha256、切块数与领域/行业/年份等元数据。"""
    __tablename__ = "sources"
    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kb: Mapped[str] = mapped_column(String(32), index=True)
    domain: Mapped[str] = mapped_column(String(32), default="")
    doc_type: Mapped[str] = mapped_column(String(16), default="law")
    original_name: Mapped[str] = mapped_column(String(300))
    stored_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    industry: Mapped[str] = mapped_column(String(100), default="")
    stage: Mapped[str] = mapped_column(String(16), default="")
    year: Mapped[str] = mapped_column(String(16), default="")
    outcome: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LedgerDiffRow(Base):
    """台账对比结果：report_id 相对 base_report_id 的增/变/解除差异 JSON（一报告一基准）。"""
    __tablename__ = "ledger_diffs"
    report_id: Mapped[str] = mapped_column(String(64), ForeignKey("reports.report_id"), primary_key=True)
    base_report_id: Mapped[str] = mapped_column(String(64))
    diff_json: Mapped[str] = mapped_column(Text)


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """建表（幂等）。"""
    Base.metadata.create_all(engine)
