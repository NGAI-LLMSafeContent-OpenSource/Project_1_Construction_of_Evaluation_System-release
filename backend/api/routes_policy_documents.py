"""
政策文档API路由
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import orchestrator
from models.schemas import PolicyDocument, get_db
from modules.policy_document_service import policy_document_service

router = APIRouter(prefix="/api/policy-documents", tags=["policy-documents"])
VALID_DOC_TYPES = {"policy", "standard", "case"}


class ManualDocCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=10)
    doc_type: str = Field(..., pattern="^(policy|standard|case)$")
    source_site: Optional[str] = "manual_input"
    source_url: Optional[str] = None


class QualityCleanRequest(BaseModel):
    dry_run: bool = True
    include_too_short: bool = False
    short_threshold: int = Field(20, ge=5, le=200)
    only_source_site: Optional[str] = "manual_input"
    allowed_doc_types: Optional[list[str]] = None


@router.post("/manual")
async def create_manual_doc(payload: ManualDocCreate, db: AsyncSession = Depends(get_db)):
    """手工录入政策/标准/案例文档。"""
    result = await policy_document_service.save_document(
        db,
        title=payload.title,
        content=payload.content,
        doc_type=payload.doc_type,
        source_site=payload.source_site or "manual_input",
        source_url=payload.source_url,
        min_relevance=0.0,
    )

    if result.get("saved"):
        return {
            "success": True,
            "message": "保存成功",
            "saved": True,
            "duplicated": False,
            "data": result,
        }

    if result.get("duplicated"):
        return {
            "success": True,
            "message": "内容已存在，未重复入库",
            "saved": False,
            "duplicated": True,
            "data": result,
        }

    reason_map = {
        "content_too_short": "内容过短，请补充后重试",
        "low_relevance": "内容相关性较低，建议补充社会主义核心价值观相关内容",
    }
    return {
        "success": False,
        "message": reason_map.get(result.get("reason", ""), "保存失败"),
        "saved": False,
        "duplicated": False,
        "reason": result.get("reason"),
        "data": result,
    }


@router.get("/")
async def list_policy_docs(
    doc_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """查询政策文档列表。"""
    query = select(PolicyDocument).order_by(desc(PolicyDocument.id))

    if doc_type:
        if doc_type not in VALID_DOC_TYPES:
            raise HTTPException(status_code=422, detail="invalid doc_type, must be policy|standard|case")
        query = query.where(PolicyDocument.doc_type == doc_type)
    if keyword:
        query = query.where(
            PolicyDocument.title.contains(keyword) | PolicyDocument.content.contains(keyword)
        )

    query = query.limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()

    items = []
    for d in docs:
        tags = []
        raw_dimension_tags = getattr(d, "dimension_tags", None)
        if isinstance(raw_dimension_tags, str) and raw_dimension_tags.strip():
            try:
                loaded = json.loads(raw_dimension_tags)
                if isinstance(loaded, list):
                    tags = loaded
            except json.JSONDecodeError:
                tags = []

        raw_created_at = getattr(d, "created_at", None)
        created_at = raw_created_at.isoformat() if isinstance(raw_created_at, datetime) else None

        raw_published_at = getattr(d, "published_at", None)
        published_at = raw_published_at.isoformat() if isinstance(raw_published_at, datetime) else None

        items.append(
            {
                "id": d.id,
                "title": d.title,
                "doc_type": d.doc_type,
                "source_site": d.source_site,
                "source_url": d.source_url,
                "publisher": d.publisher,
                "relevance_score": d.relevance_score,
                "dimension_tags": tags,
                "created_at": created_at,
                "published_at": published_at,
            }
        )

    payload = {"total": len(items), "items": items}
    return {"success": True, "data": payload, **payload}


@router.post("/crawl/trigger")
async def trigger_crawl(db: AsyncSession = Depends(get_db)):
    """手动触发一次政策抓取。"""
    result = await orchestrator.policy_agent.crawl_latest_documents(db=db)
    return {"success": True, "data": result, **result}


@router.get("/crawl/status")
async def crawl_status():
    """获取最近一次抓取状态。"""
    status = orchestrator.policy_agent.get_last_crawl_status()
    return {"success": True, "data": status, **status}


@router.get("/quality/report")
async def quality_report(
    sample_limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """查看政策文档数据质量报告（乱码/过短）。"""
    data = await policy_document_service.build_quality_report(db, sample_limit=sample_limit)
    return {"success": True, "data": data}


@router.post("/quality/clean")
async def quality_clean(payload: QualityCleanRequest, db: AsyncSession = Depends(get_db)):
    """清洗疑似乱码和可选过短文档，默认 dry_run。"""
    result = await policy_document_service.clean_documents(
        db,
        dry_run=payload.dry_run,
        include_too_short=payload.include_too_short,
        short_threshold=payload.short_threshold,
        only_source_site=payload.only_source_site,
        allowed_doc_types=payload.allowed_doc_types,
    )
    return {"success": True, "data": result}
