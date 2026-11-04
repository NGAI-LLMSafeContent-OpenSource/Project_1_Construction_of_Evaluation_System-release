"""
人机协作审校模块
功能：指标的增删查改、专家审核、闭环反馈
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import Indicator

try:
    from agents.indicator_generator import PREDEFINED_INDICATORS
    from ontology.new_indicator_taxonomy import LEVEL2_TO_ITEM
except ImportError:
    from backend.agents.indicator_generator import PREDEFINED_INDICATORS
    from backend.ontology.new_indicator_taxonomy import LEVEL2_TO_ITEM


PREDEFINED_INDICATOR_MAP = {}
for item in PREDEFINED_INDICATORS:
    key = str(item.get("level3") or item.get("level2") or item.get("name") or "").strip()
    if key:
        normalized = dict(item)
        normalized["name"] = normalized.get("level3") or normalized.get("level2") or key
        normalized["level3"] = normalized.get("level3") or ""
        PREDEFINED_INDICATOR_MAP[key] = normalized


class ReviewModule:
    """人机协作审校模块"""

    async def get_all_indicators(self, db: AsyncSession, status: Optional[str] = None) -> List[Dict]:
        """获取所有指标"""
        query = select(Indicator)
        if status:
            query = query.where(Indicator.status == status)
        query = query.order_by(Indicator.id)

        result = await db.execute(query)
        indicators = result.scalars().all()

        return [self._to_dict(ind) for ind in indicators]

    async def get_indicator_by_id(self, db: AsyncSession, indicator_id: int) -> Optional[Dict]:
        """根据 ID 获取指标"""
        result = await db.execute(select(Indicator).where(Indicator.id == indicator_id))
        indicator = result.scalar_one_or_none()
        return self._to_dict(indicator) if indicator else None

    async def create_indicator(self, db: AsyncSession, data: Dict) -> Dict:
        """新增指标"""
        indicator = Indicator(
            name=data.get("name"),
            level1=data.get("level1"),
            level2=data.get("level2"),
            level3=data.get("level3"),
            level4=data.get("level4"),
            definition=data.get("definition"),
            formula=data.get("formula"),
            source=data.get("source"),
            dimension=data.get("dimension"),
            formula_type=data.get("formula_type") or "",
            explain_reason=data.get("explain_reason"),
            positive_example=data.get("positive_example"),
            negative_example=data.get("negative_example"),
            scoring_rule=data.get("scoring_rule") or data.get("formula"),
            skill_name=data.get("skill_name") or "",
            demo_flow=data.get("demo_flow"),
            status=data.get("status") or "pending",
            created_at=datetime.utcnow(),
        )
        db.add(indicator)
        await db.commit()
        await db.refresh(indicator)
        return self._to_dict(indicator)

    async def update_indicator(self, db: AsyncSession, indicator_id: int, data: Dict) -> Optional[Dict]:
        """修改指标"""
        result = await db.execute(select(Indicator).where(Indicator.id == indicator_id))
        indicator = result.scalar_one_or_none()

        if not indicator:
            return None

        allow_review_status_transition = bool(data.pop("_allow_review_status_transition", False))

        for key, value in data.items():
            if hasattr(indicator, key) and value is not None:
                if key == "status" and value in {"approved", "ignored", "rejected"} and not allow_review_status_transition:
                    continue
                setattr(indicator, key, value)

        setattr(indicator, "updated_at", datetime.utcnow())
        await db.commit()
        await db.refresh(indicator)
        return self._to_dict(indicator)

    async def delete_indicator(self, db: AsyncSession, indicator_id: int) -> bool:
        """删除指标"""
        result = await db.execute(select(Indicator).where(Indicator.id == indicator_id))
        indicator = result.scalar_one_or_none()

        if not indicator:
            return False

        await db.delete(indicator)
        await db.commit()
        return True

    async def approve_indicator(self, db: AsyncSession, indicator_id: int, comment: str = "") -> Optional[Dict]:
        """采纳指标"""
        return await self.update_indicator(db, indicator_id, {
            "status": "approved",
            "review_comment": comment,
            "_allow_review_status_transition": True,
        })

    async def reject_indicator(self, db: AsyncSession, indicator_id: int, comment: str = "") -> Optional[Dict]:
        """忽略/拒绝指标"""
        return await self.update_indicator(db, indicator_id, {
            "status": "ignored",
            "review_comment": comment,
            "_allow_review_status_transition": True,
        })

    def _existing_indicator_query(self, ind_data: Dict):
        level1 = ind_data.get("level1")
        level2 = ind_data.get("level2")
        level3 = ind_data.get("level3")

        if level3:
            return select(Indicator).where(
                Indicator.level1 == level1,
                Indicator.level2 == level2,
                Indicator.level3 == level3,
            )

        if level2:
            return select(Indicator).where(
                Indicator.level1 == level1,
                Indicator.level2 == level2,
                or_(Indicator.level3 == None, Indicator.level3 == ""),
            )

        return select(Indicator).where(
            Indicator.level1 == level1,
            or_(Indicator.level2 == None, Indicator.level2 == ""),
            or_(Indicator.level3 == None, Indicator.level3 == ""),
        )

    async def batch_import(self, db: AsyncSession, indicators: List[Dict]) -> int:
        """批量导入指标"""
        count = 0
        for ind_data in indicators:
            existing = await db.execute(self._existing_indicator_query(ind_data))
            if existing.scalar_one_or_none() is None:
                await self.create_indicator(db, {**ind_data, "status": "pending"})
                count += 1
        return count

    def _to_dict(self, indicator: Indicator) -> Dict:
        """转换为字典"""
        if not indicator:
            return {}

        created_at: Optional[datetime] = None
        updated_at: Optional[datetime] = None

        raw_created_at = getattr(indicator, "created_at", None)
        if isinstance(raw_created_at, datetime):
            created_at = raw_created_at

        raw_updated_at = getattr(indicator, "updated_at", None)
        if isinstance(raw_updated_at, datetime):
            updated_at = raw_updated_at

        filled = self._fill_from_predefined(indicator)

        return {
            **filled,
            "id": indicator.id,
            "name": filled.get("name"),
            "level1": filled.get("level1"),
            "level2": filled.get("level2"),
            "level3": filled.get("level3"),
            "level4": getattr(indicator, "level4", None),
            "definition": filled.get("definition"),
            "formula": filled.get("formula"),
            "source": filled.get("source"),
            "dimension": filled.get("dimension"),
            "formula_type": filled.get("formula_type"),
            "explain_reason": filled.get("explain_reason"),
            "positive_example": filled.get("positive_example"),
            "negative_example": filled.get("negative_example"),
            "scoring_rule": filled.get("scoring_rule"),
            "skill_name": filled.get("skill_name"),
            "demo_flow": filled.get("demo_flow"),
            "status": indicator.status,
            "review_comment": indicator.review_comment,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

    def _fill_from_predefined(self, indicator: Indicator) -> Dict:
        key = str(getattr(indicator, "level3", None) or "").strip()
        if not key:
            key = str(getattr(indicator, "level2", None) or getattr(indicator, "name", None) or "").strip()
        base = PREDEFINED_INDICATOR_MAP.get(key, {})
        parent_level2 = str(getattr(indicator, "level2", None) or "").strip()
        parent_base = LEVEL2_TO_ITEM.get(parent_level2, {})
        return {
            "name": getattr(indicator, "name", None) or base.get("name") or parent_base.get("name"),
            "level1": getattr(indicator, "level1", None) or base.get("level1") or parent_base.get("level1"),
            "level2": getattr(indicator, "level2", None) or base.get("level2") or parent_base.get("level2"),
            "level3": getattr(indicator, "level3", None) or base.get("level3"),
            "layer_name": getattr(indicator, "layer_name", None) or base.get("layer_name") or parent_base.get("layer_name"),
            "definition": getattr(indicator, "definition", None) or base.get("definition") or parent_base.get("definition"),
            "formula": getattr(indicator, "formula", None) or base.get("formula") or parent_base.get("formula"),
            "source": getattr(indicator, "source", None) or base.get("source") or parent_base.get("source"),
            "dimension": getattr(indicator, "dimension", None) or base.get("dimension") or parent_base.get("dimension"),
            "formula_type": getattr(indicator, "formula_type", None) or base.get("formula_type") or parent_base.get("formula_type"),
            "explain_reason": getattr(indicator, "explain_reason", None) or base.get("explain_reason") or parent_base.get("explain_reason"),
            "positive_example": getattr(indicator, "positive_example", None) or base.get("positive_example") or parent_base.get("positive_example"),
            "negative_example": getattr(indicator, "negative_example", None) or base.get("negative_example") or parent_base.get("negative_example"),
            "scoring_rule": getattr(indicator, "scoring_rule", None) or base.get("scoring_rule") or parent_base.get("scoring_rule") or base.get("formula") or parent_base.get("formula"),
            "skill_name": getattr(indicator, "skill_name", None) or base.get("skill_name") or parent_base.get("skill_name"),
            "demo_flow": getattr(indicator, "demo_flow", None) or base.get("demo_flow") or parent_base.get("demo_flow"),
        }


review_module = ReviewModule()
