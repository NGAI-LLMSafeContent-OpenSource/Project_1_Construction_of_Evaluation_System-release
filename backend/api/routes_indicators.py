"""
指标管理API路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from models.schemas import get_db
from modules.review_module import review_module
from ontology.new_indicator_taxonomy import ALLOWED_DIMENSIONS, LEVEL1_TO_DIMENSION, LEVEL2_TO_ITEM, NEW_INDICATOR_ONTOLOGY

router = APIRouter(prefix="/api/indicators", tags=["indicators"])

class IndicatorCreate(BaseModel):
    name: str
    level1: Optional[str] = None
    level2: Optional[str] = None
    level3: Optional[str] = None
    level4: Optional[str] = None
    definition: Optional[str] = None
    formula: Optional[str] = None
    source: Optional[str] = None
    dimension: Optional[str] = None
    formula_type: Optional[str] = None
    explain_reason: Optional[str] = None
    positive_example: Optional[str] = None
    negative_example: Optional[str] = None
    scoring_rule: Optional[str] = None
    skill_name: Optional[str] = None
    demo_flow: Optional[str] = None

class IndicatorUpdate(BaseModel):
    name: Optional[str] = None
    level1: Optional[str] = None
    level2: Optional[str] = None
    level3: Optional[str] = None
    level4: Optional[str] = None
    definition: Optional[str] = None
    formula: Optional[str] = None
    source: Optional[str] = None
    dimension: Optional[str] = None
    formula_type: Optional[str] = None
    explain_reason: Optional[str] = None
    positive_example: Optional[str] = None
    negative_example: Optional[str] = None
    scoring_rule: Optional[str] = None
    skill_name: Optional[str] = None
    demo_flow: Optional[str] = None
    status: Optional[str] = None
    review_comment: Optional[str] = None

class ReviewAction(BaseModel):
    comment: Optional[str] = ""

@router.get("/")
async def get_indicators(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """获取指标列表"""
    indicators = await review_module.get_all_indicators(db, status)
    return {"indicators": indicators, "total": len(indicators)}

@router.post("/")
async def create_indicator(data: IndicatorCreate, db: AsyncSession = Depends(get_db)):
    """新增指标"""
    indicator = await review_module.create_indicator(db, data.dict())
    return indicator

@router.put("/{indicator_id}")
async def update_indicator(indicator_id: int, data: IndicatorUpdate, db: AsyncSession = Depends(get_db)):
    """修改指标"""
    if data.status in {"approved", "ignored", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="采纳/忽略必须通过人工审核接口执行，不能通过通用修改接口直接变更状态",
        )

    update_data = {k: v for k, v in data.dict().items() if v is not None}
    indicator = await review_module.update_indicator(db, indicator_id, update_data)
    if not indicator:
        raise HTTPException(status_code=404, detail="指标不存在")
    return indicator

@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: int, db: AsyncSession = Depends(get_db)):
    """删除指标"""
    success = await review_module.delete_indicator(db, indicator_id)
    if not success:
        raise HTTPException(status_code=404, detail="指标不存在")
    return {"message": "删除成功"}

@router.post("/{indicator_id}/approve")
async def approve_indicator(indicator_id: int, action: ReviewAction, db: AsyncSession = Depends(get_db)):
    """采纳指标"""
    indicator = await review_module.approve_indicator(db, indicator_id, action.comment or "")
    if not indicator:
        raise HTTPException(status_code=404, detail="指标不存在")
    return indicator

@router.post("/{indicator_id}/reject")
async def reject_indicator(indicator_id: int, action: ReviewAction, db: AsyncSession = Depends(get_db)):
    """忽略/拒绝指标"""
    indicator = await review_module.reject_indicator(db, indicator_id, action.comment or "")
    if not indicator:
        raise HTTPException(status_code=404, detail="指标不存在")
    return indicator

@router.get("/stats/summary")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取指标统计信息"""
    all_indicators = await review_module.get_all_indicators(db)
    
    stats = {
        "total": len(all_indicators),
        "pending": len([i for i in all_indicators if i.get("status") == "pending"]),
        "approved": len([i for i in all_indicators if i.get("status") == "approved"]),
        "ignored": len([i for i in all_indicators if i.get("status") in {"ignored", "rejected"}]),
        "by_dimension": {}
    }
    
    for ind in all_indicators:
        dim = ind.get("dimension", "unknown")
        stats["by_dimension"][dim] = stats["by_dimension"].get(dim, 0) + 1
    
    return stats


@router.get("/framework")
async def get_indicator_framework(db: AsyncSession = Depends(get_db)):
    """Return fixed top/level1/level2 nodes plus approved level-3 indicators."""
    approved_indicators = await review_module.get_all_indicators(db, status="approved")

    level3_by_level2 = {}
    for ind in approved_indicators:
        level2 = (ind.get("level2") or "").strip()
        level3 = (ind.get("level3") or "").strip()
        if level2 in LEVEL2_TO_ITEM and level3:
            level3_by_level2.setdefault(level2, []).append(ind)

    dimensions = []
    total_l3 = 0
    for dimension, layer_name in ALLOWED_DIMENSIONS.items():
        level1_names = [name for name, dim in LEVEL1_TO_DIMENSION.items() if dim == dimension]
        level1_nodes = []
        for level1 in level1_names:
            level2_nodes = []
            for item in NEW_INDICATOR_ONTOLOGY:
                if item["level1"] != level1:
                    continue
                children = level3_by_level2.get(item["level2"], [])
                total_l3 += len(children)
                level2_nodes.append(
                    {
                        **item,
                        "children": children,
                        "count": len(children),
                    }
                )
            level1_nodes.append({"name": level1, "children": level2_nodes, "count": sum(x["count"] for x in level2_nodes)})
        dimensions.append({"name": layer_name, "dimension": dimension, "children": level1_nodes, "count": sum(x["count"] for x in level1_nodes)})

    return {
        "success": True,
        "data": {
            "dimensions": dimensions,
            "summary": {
                "level1_count": len(dimensions),
                "level2_count": len(NEW_INDICATOR_ONTOLOGY),
                "level3_count": total_l3,
            },
        },
    }


@router.get("/{indicator_id}")
async def get_indicator(indicator_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个指标"""
    indicator = await review_module.get_indicator_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(status_code=404, detail="指标不存在")
    return indicator
