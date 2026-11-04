"""
案例库API路由
"""
import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from models.schemas import get_db, CaseItem
from modules.evolution_module import evolution_module

router = APIRouter(prefix="/api/cases", tags=["cases"])

class CaseCreate(BaseModel):
    title: str
    content: str
    dimension: Optional[str] = None
    indicator_name: Optional[str] = None
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class EvolutionRequest(BaseModel):
    content: str
    content_type: str = "policy"  # policy/standard/case

@router.get("/")
async def get_cases(dimension: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """获取案例列表"""
    query = select(CaseItem)
    if dimension:
        query = query.where(CaseItem.dimension == dimension)
    query = query.order_by(CaseItem.id.desc())
    
    result = await db.execute(query)
    cases = result.scalars().all()

    case_items = []
    for c in cases:
        raw_tags = getattr(c, "tags", None)
        tags: List[str] = []
        if isinstance(raw_tags, str) and raw_tags.strip():
            try:
                parsed_tags = json.loads(raw_tags)
                if isinstance(parsed_tags, list):
                    tags = parsed_tags
            except json.JSONDecodeError:
                tags = []

        raw_created_at = getattr(c, "created_at", None)
        created_at = raw_created_at.isoformat() if isinstance(raw_created_at, datetime) else None

        case_items.append(
            {
                "id": c.id,
                "title": c.title,
                "content": c.content,
                "dimension": c.dimension,
                "indicator_name": c.indicator_name,
                "source": c.source,
                "tags": tags,
                "created_at": created_at,
            }
        )
    
    return {
        "cases": case_items,
        "total": len(cases)
    }

@router.post("/")
async def create_case(data: CaseCreate, db: AsyncSession = Depends(get_db)):
    """新增案例"""
    case = CaseItem(
        title=data.title,
        content=data.content,
        dimension=data.dimension,
        indicator_name=data.indicator_name,
        source=data.source,
        tags=json.dumps(data.tags or [], ensure_ascii=False)
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return {"id": case.id, "message": "案例创建成功"}

@router.post("/generate")
async def generate_cases(indicator_name: str, dimension: str, 
                          context: str = "", db: AsyncSession = Depends(get_db)):
    """为指标自动生成案例"""
    cases = await evolution_module.generate_case(indicator_name, dimension, context)
    
    saved_cases = []
    for case_type, case_data in [("positive", cases.get("positive_case", {})), 
                                   ("negative", cases.get("negative_case", {}))]:
        if case_data.get("title"):
            case = CaseItem(
                title=case_data["title"],
                content=case_data["content"],
                dimension=dimension,
                indicator_name=indicator_name,
                source="AI自动生成",
                tags=json.dumps(case_data.get("tags", []), ensure_ascii=False)
            )
            db.add(case)
            saved_cases.append(case_data)
    
    await db.commit()
    return {"cases": saved_cases, "message": f"成功生成 {len(saved_cases)} 个案例"}

@router.post("/evolution/trigger")
async def trigger_evolution(request: EvolutionRequest, db: AsyncSession = Depends(get_db)):
    """触发自主演化更新"""
    result = await evolution_module.trigger_incremental_update(
        request.content, 
        request.content_type
    )
    
    # 保存新生成的案例
    for case_data in result.get("new_cases", []):
        case = CaseItem(
            title=case_data.get("title", ""),
            content=case_data.get("content", ""),
            dimension=case_data.get("dimension", ""),
            indicator_name=case_data.get("indicator_name", ""),
            source="演化更新",
            tags=json.dumps([], ensure_ascii=False)
        )
        db.add(case)
    
    if result.get("new_cases"):
        await db.commit()
    
    return result
