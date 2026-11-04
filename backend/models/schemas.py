from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import async_sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chroma_db/value_eval_main.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Indicator(Base):
    """评估指标模型"""
    __tablename__ = "indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    level1 = Column(String(50))   # 一级指标
    level2 = Column(String(50))   # 二级指标
    level3 = Column(String(50))   # 三级指标
    level4 = Column(String(80))   # 四级指标（可选）
    definition = Column(Text)
    formula = Column(Text)
    source = Column(Text)         # 来源依据
    status = Column(String(20), default="pending")  # pending/approved/rejected/modified
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    review_comment = Column(Text)
    dimension = Column(String(50))  # culture_adapt/scene_support
    formula_type = Column(String(20))
    explain_reason = Column(Text)
    positive_example = Column(Text)
    negative_example = Column(Text)
    scoring_rule = Column(Text)
    skill_name = Column(String(100))
    demo_flow = Column(Text)

class CaseItem(Base):
    """案例库模型"""
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    content = Column(Text)
    dimension = Column(String(50))
    indicator_name = Column(String(100))
    source = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    tags = Column(Text)  # JSON格式存储标签

class AgentLog(Base):
    """智能体运行日志"""
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100))
    task_id = Column(String(100))
    status = Column(String(20))  # running/completed/failed
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class PolicyDocument(Base):
    """政策文档存储"""
    __tablename__ = "policy_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    content = Column(Text)
    doc_type = Column(String(50))  # policy/standard/case
    source_site = Column(String(100))
    source_url = Column(String(500))
    publisher = Column(String(200))
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    relevance_score = Column(Float, default=0.0)
    dimension_tags = Column(Text, default="[]")
    content_hash = Column(String(64), unique=True, index=True)
    crawl_batch_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CrawlRun(Base):
    """抓取任务批次汇总"""
    __tablename__ = "crawl_runs"

    id = Column(Integer, primary_key=True, index=True)
    crawl_batch_id = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default="running")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    saved = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    skipped_low_relevance = Column(Integer, default=0)
    errors_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)


class CrawlRunItem(Base):
    """抓取任务明细（每个来源URL一条）"""
    __tablename__ = "crawl_run_items"

    id = Column(Integer, primary_key=True, index=True)
    crawl_batch_id = Column(String(100), index=True, nullable=False)
    source_site = Column(String(100))
    source_url = Column(String(500))
    http_status = Column(Integer, nullable=True)
    parse_ok = Column(Boolean, default=False)
    save_status = Column(String(30), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IndicatorNode(Base):
    """指标树节点（一级/二级/三级）"""
    __tablename__ = "indicator_nodes"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("indicator_nodes.id"), nullable=True)
    level = Column(Integer, nullable=False)  # 1/2/3
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class IndicatorRelation(Base):
    """指标关系边"""
    __tablename__ = "indicator_relations"

    id = Column(Integer, primary_key=True, index=True)
    from_node_id = Column(Integer, ForeignKey("indicator_nodes.id"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("indicator_nodes.id"), nullable=False)
    relation_type = Column(String(30), nullable=False)
    confidence = Column(Float, default=0.0)
    evidence_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExtractionRun(Base):
    """维度/指标抽取任务批次"""
    __tablename__ = "extraction_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), unique=True, index=True, nullable=False)
    model_name = Column(String(100), nullable=True)
    input_doc_count = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    quality_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExtractedCandidate(Base):
    """智能体抽取候选（待审校）"""
    __tablename__ = "extracted_candidates"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), index=True, nullable=False)
    doc_id = Column(Integer, ForeignKey("policy_documents.id"), nullable=True)
    parent_l1_id = Column(Integer, ForeignKey("indicator_nodes.id"), nullable=True)
    parent_l2_id = Column(Integer, ForeignKey("indicator_nodes.id"), nullable=True)
    candidate_name = Column(String(150), nullable=False)
    confidence = Column(Float, default=0.0)
    evidence_text = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending/accepted/rejected/edited
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewTask(Base):
    """人机协作审校记录"""
    __tablename__ = "review_tasks"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("extracted_candidates.id"), nullable=False)
    reviewer = Column(String(100), nullable=True)
    action = Column(String(20), nullable=False)  # accept/reject/edit
    edited_name = Column(String(150), nullable=True)
    comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow)

async def _migrate_policy_documents_columns(conn):
    """轻量迁移：为已存在的SQLite表补充新字段。"""
    result = await conn.exec_driver_sql("PRAGMA table_info(policy_documents)")
    existing = {row[1] for row in result.fetchall()}

    migrations = [
        ("source_site", "ALTER TABLE policy_documents ADD COLUMN source_site VARCHAR(100)"),
        ("publisher", "ALTER TABLE policy_documents ADD COLUMN publisher VARCHAR(200)"),
        ("published_at", "ALTER TABLE policy_documents ADD COLUMN published_at DATETIME"),
        ("fetched_at", "ALTER TABLE policy_documents ADD COLUMN fetched_at DATETIME"),
        ("relevance_score", "ALTER TABLE policy_documents ADD COLUMN relevance_score FLOAT DEFAULT 0.0"),
        ("dimension_tags", "ALTER TABLE policy_documents ADD COLUMN dimension_tags TEXT DEFAULT '[]'"),
        ("content_hash", "ALTER TABLE policy_documents ADD COLUMN content_hash VARCHAR(64)"),
        ("crawl_batch_id", "ALTER TABLE policy_documents ADD COLUMN crawl_batch_id VARCHAR(100)"),
    ]

    for column_name, sql in migrations:
        if column_name not in existing:
            await conn.exec_driver_sql(sql)

    await conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_policy_documents_content_hash ON policy_documents (content_hash)"
    )


async def _migrate_indicators_columns(conn):
    """轻量迁移：为已存在的indicators表补充新字段。"""
    result = await conn.exec_driver_sql("PRAGMA table_info(indicators)")
    existing = {row[1] for row in result.fetchall()}

    migrations = [
        ("level4", "ALTER TABLE indicators ADD COLUMN level4 VARCHAR(80)"),
        ("formula_type", "ALTER TABLE indicators ADD COLUMN formula_type VARCHAR(20)"),
        ("explain_reason", "ALTER TABLE indicators ADD COLUMN explain_reason TEXT"),
        ("positive_example", "ALTER TABLE indicators ADD COLUMN positive_example TEXT"),
        ("negative_example", "ALTER TABLE indicators ADD COLUMN negative_example TEXT"),
        ("scoring_rule", "ALTER TABLE indicators ADD COLUMN scoring_rule TEXT"),
        ("skill_name", "ALTER TABLE indicators ADD COLUMN skill_name VARCHAR(100)"),
        ("demo_flow", "ALTER TABLE indicators ADD COLUMN demo_flow TEXT"),
    ]

    for column_name, sql in migrations:
        if column_name not in existing:
            await conn.exec_driver_sql(sql)


async def _seed_indicator_l1_nodes(conn):
    """初始化一级指标根节点（幂等）。"""
    result = await conn.exec_driver_sql("SELECT name FROM indicator_nodes WHERE level = 1")
    existing = {row[0] for row in result.fetchall()}

    root_nodes = [
        "文化适配层",
        "场景支撑层",
    ]

    for node_name in root_nodes:
        if node_name in existing:
            continue
        await conn.exec_driver_sql(
            "INSERT INTO indicator_nodes (parent_id, level, name, status, created_at, updated_at) "
            "VALUES (NULL, 1, :name, 'active', :now, :now)",
            {"name": node_name, "now": datetime.utcnow()},
        )

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_policy_documents_columns(conn)
        await _migrate_indicators_columns(conn)
        await _seed_indicator_l1_nodes(conn)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
