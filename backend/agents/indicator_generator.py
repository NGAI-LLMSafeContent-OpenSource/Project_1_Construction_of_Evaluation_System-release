"""Indicator generation agent for multi-level candidate mining."""

import json
import re
from typing import Dict, List, Optional

try:
    from ontology.new_indicator_taxonomy import (
        ALLOWED_DIMENSIONS,
        ALLOWED_LEVEL1,
        LEVEL1_DEFINITIONS,
        LEVEL1_TO_DIMENSION,
        LEVEL2_TO_LEVEL1,
        NEW_INDICATOR_ONTOLOGY,
    )
    from utils.llm_client import llm_invoke
except ImportError:
    from backend.ontology.new_indicator_taxonomy import (
        ALLOWED_DIMENSIONS,
        ALLOWED_LEVEL1,
        LEVEL1_DEFINITIONS,
        LEVEL1_TO_DIMENSION,
        LEVEL2_TO_LEVEL1,
        NEW_INDICATOR_ONTOLOGY,
    )
    from backend.utils.llm_client import llm_invoke


LEVEL3_SYSTEM_PROMPT = """你是数据评估指标设计专家。当前正式体系固定为：
- 顶层：文化适配层、场景支撑层
- 一级指标：文化忠实度、伦理敏感度、语义稀缺度、任务关联度
- 二级指标固定为用户给定的 12 项
你只能在固定二级指标下面生成三级指标。不得新增一级指标、二级指标或顶层维度。
每个候选三级指标必须归属到一个固定二级指标下面。输出必须是可解析 JSON，不要输出 Markdown。"""

LEVEL1_SYSTEM_PROMPT = """你是数据评估指标设计专家。请基于输入政策文档挖掘新的一级指标候选。
要求：
1. 只生成新的一级指标，不要生成二级或三级指标。
2. 不能与现有固定一级指标重复。
3. 名称要具体、可审校，不要输出口号化表述。
4. 输出必须是可解析 JSON，不要输出 Markdown。"""

LEVEL2_SYSTEM_PROMPT = """你是数据评估指标设计专家。请基于输入政策文档挖掘新的二级指标候选。
要求：
1. 只能挂在已有一级指标下面，不得新增一级指标。
2. 不能与现有固定二级指标重复。
3. 不要生成三级指标。
4. 输出必须是可解析 JSON，不要输出 Markdown。"""


def _ontology_item_to_indicator(item: Dict) -> Dict:
    normalized = dict(item)
    normalized["name"] = normalized.get("level2")
    normalized["formula"] = normalized.get("scoring_rule")
    normalized.setdefault("status", "approved")
    return normalized


PREDEFINED_INDICATORS = [_ontology_item_to_indicator(item) for item in NEW_INDICATOR_ONTOLOGY]


class IndicatorGeneratorAgent:
    """Generate candidate indicators according to the requested mining level."""

    def __init__(self):
        self.agent_name = "IndicatorGeneratorAgent"

    @staticmethod
    def _default_parent(matching_result: Optional[Dict] = None) -> Dict:
        matched_l2 = (matching_result or {}).get("matched_level2") or []
        for level2 in matched_l2:
          if level2 in LEVEL2_TO_LEVEL1:
                level1 = LEVEL2_TO_LEVEL1[level2]
                dimension = LEVEL1_TO_DIMENSION[level1]
                return {
                    "dimension": dimension,
                    "layer_name": ALLOWED_DIMENSIONS[dimension],
                    "level1": level1,
                    "level2": level2,
                }

        return {
            "dimension": "scene_support",
            "layer_name": ALLOWED_DIMENSIONS.get("scene_support", ""),
            "level1": "任务关联度",
            "level2": "语义匹配度",
        }

    @staticmethod
    def _extract_first_json_object(text: str) -> Optional[Dict]:
        if not text:
            return None
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group())
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", "", str(value or "")).strip().lower()

    @classmethod
    def _normalize_generated_level1_item(cls, raw: Dict) -> Optional[Dict]:
        if not isinstance(raw, dict):
            return None

        level1 = str(raw.get("level1") or raw.get("name") or "").strip()
        if not level1:
            return None

        dimension = str(raw.get("dimension") or "").strip()
        if dimension not in ALLOWED_DIMENSIONS and level1 in LEVEL1_TO_DIMENSION:
            dimension = LEVEL1_TO_DIMENSION[level1]
        if dimension not in ALLOWED_DIMENSIONS:
            dimension = ""

        return {
            "dimension": dimension,
            "layer_name": ALLOWED_DIMENSIONS.get(dimension, ""),
            "level1": level1,
            "level2": "",
            "level3": "",
            "name": level1,
            "definition": str(raw.get("definition") or "").strip(),
            "positive_example": str(raw.get("positive_example") or "").strip(),
            "negative_example": str(raw.get("negative_example") or "").strip(),
            "source": str(raw.get("source_evidence") or raw.get("source") or "LLM 动态生成").strip(),
            "status": "pending",
        }

    @classmethod
    def _normalize_generated_level2_item(cls, raw: Dict) -> Optional[Dict]:
        if not isinstance(raw, dict):
            return None

        level1 = str(raw.get("level1") or "").strip()
        level2 = str(raw.get("level2") or raw.get("name") or "").strip()
        if not (level1 and level2):
            return None

        dimension = LEVEL1_TO_DIMENSION.get(level1, str(raw.get("dimension") or "").strip())
        if dimension not in ALLOWED_DIMENSIONS:
            dimension = ""

        return {
            "dimension": dimension,
            "layer_name": ALLOWED_DIMENSIONS.get(dimension, ""),
            "level1": level1,
            "level2": level2,
            "level3": "",
            "name": level2,
            "definition": str(raw.get("definition") or "").strip(),
            "positive_example": str(raw.get("positive_example") or "").strip(),
            "negative_example": str(raw.get("negative_example") or "").strip(),
            "source": str(raw.get("source_evidence") or raw.get("source") or "LLM 动态生成").strip(),
            "status": "pending",
        }

    @staticmethod
    def _normalize_generated_level3_item(raw: Dict, matching_result: Optional[Dict] = None) -> Optional[Dict]:
        if not isinstance(raw, dict):
            return None

        level2 = str(raw.get("level2") or "").strip()
        if level2 not in LEVEL2_TO_LEVEL1:
            level2 = IndicatorGeneratorAgent._default_parent(matching_result)["level2"]

        level1 = LEVEL2_TO_LEVEL1[level2]
        dimension = LEVEL1_TO_DIMENSION[level1]
        level3 = str(raw.get("level3") or raw.get("name") or "").strip()
        if not level3:
            return None

        return {
            "dimension": dimension,
            "layer_name": ALLOWED_DIMENSIONS[dimension],
            "level1": level1,
            "level2": level2,
            "level3": level3,
            "name": level3,
            "definition": str(raw.get("definition") or "").strip(),
            "positive_example": str(raw.get("positive_example") or "").strip(),
            "negative_example": str(raw.get("negative_example") or "").strip(),
            "source": str(raw.get("source_evidence") or raw.get("source") or "LLM 动态生成").strip(),
            "status": "pending",
        }

    def _filter_level1_duplicates(self, items: List[Dict]) -> List[Dict]:
        fixed_names = {self._normalize_text(name) for name in ALLOWED_LEVEL1}
        seen = set()
        filtered = []

        for item in items:
            level1 = self._normalize_text(item.get("level1"))
            if not level1 or level1 in fixed_names or level1 in seen:
                continue
            seen.add(level1)
            filtered.append(item)
        return filtered

    def _filter_level2_duplicates(self, items: List[Dict]) -> List[Dict]:
        fixed_paths = {
            (self._normalize_text(level1), self._normalize_text(level2))
            for level2, level1 in LEVEL2_TO_LEVEL1.items()
        }
        seen = set()
        filtered = []

        for item in items:
            level1 = self._normalize_text(item.get("level1"))
            level2 = self._normalize_text(item.get("level2"))
            if not level1 or not level2:
                continue
            if level1 not in {self._normalize_text(name) for name in ALLOWED_LEVEL1}:
                continue
            path = (level1, level2)
            if path in fixed_paths or path in seen:
                continue
            seen.add(path)
            filtered.append(item)
        return filtered

    async def generate_level1_indicators(self, context: str = "") -> Dict:
        if not context:
            return {"items": [], "llm_fallback": False, "llm_error": ""}

        user_prompt = f"""请基于输入政策文档，挖掘可能新增的一级指标。
现有固定一级指标如下：
{json.dumps(sorted(ALLOWED_LEVEL1), ensure_ascii=False, indent=2)}

现有一级指标定义如下：
{json.dumps(LEVEL1_DEFINITIONS, ensure_ascii=False, indent=2)}

输入文本摘要：
{context[:6000]}

请生成 1-5 个新的一级指标候选。
返回 JSON：
{{
  "indicators": [
    {{
      "level1": "一级指标名称",
      "dimension": "culture_adapt 或 scene_support，可为空",
      "definition": "一级指标定义",
      "positive_example": "正例，可为空",
      "negative_example": "反例，可为空",
      "source_evidence": "来自输入文档的依据"
    }}
  ]
}}"""

        try:
            response = await llm_invoke(LEVEL1_SYSTEM_PROMPT, user_prompt, temperature=0.4)
        except Exception as exc:
            return {"items": [], "llm_fallback": True, "llm_error": str(exc)}

        parsed = self._extract_first_json_object(response)
        if not parsed:
            return {"items": [], "llm_fallback": True, "llm_error": "llm_json_parse_failed"}

        normalized_items = [
            item
            for item in (
                self._normalize_generated_level1_item(raw)
                for raw in parsed.get("indicators", [])
            )
            if item
        ]
        return {
            "items": self._filter_level1_duplicates(normalized_items),
            "llm_fallback": False,
            "llm_error": "",
        }

    async def generate_level2_indicators(self, context: str = "") -> Dict:
        if not context:
            return {"items": [], "llm_fallback": False, "llm_error": ""}

        user_prompt = f"""请基于输入政策文档，挖掘可能新增的二级指标。
要求：
1. 只能挂在以下已有一级指标下面：
{json.dumps(sorted(ALLOWED_LEVEL1), ensure_ascii=False, indent=2)}
2. 不能与以下固定二级指标重复：
{json.dumps(LEVEL2_TO_LEVEL1, ensure_ascii=False, indent=2)}
3. 不要新增一级指标，不要生成三级指标。

输入文本摘要：
{context[:6000]}

请生成 1-5 个新的二级指标候选。
返回 JSON：
{{
  "indicators": [
    {{
      "level1": "已有一级指标名称",
      "level2": "新增二级指标名称",
      "definition": "二级指标定义",
      "positive_example": "正例，可为空",
      "negative_example": "反例，可为空",
      "source_evidence": "来自输入文档的依据"
    }}
  ]
}}"""

        try:
            response = await llm_invoke(LEVEL2_SYSTEM_PROMPT, user_prompt, temperature=0.4)
        except Exception as exc:
            return {"items": [], "llm_fallback": True, "llm_error": str(exc)}

        parsed = self._extract_first_json_object(response)
        if not parsed:
            return {"items": [], "llm_fallback": True, "llm_error": "llm_json_parse_failed"}

        normalized_items = [
            item
            for item in (
                self._normalize_generated_level2_item(raw)
                for raw in parsed.get("indicators", [])
            )
            if item
        ]
        return {
            "items": self._filter_level2_duplicates(normalized_items),
            "llm_fallback": False,
            "llm_error": "",
        }

    async def generate_level3_indicators(
        self,
        context: str = "",
        matching_result: Optional[Dict] = None,
    ) -> Dict:
        if not context:
            return {"items": [], "llm_fallback": False, "llm_error": ""}

        allowed_level2 = list(LEVEL2_TO_LEVEL1.keys())
        user_prompt = f"""请基于输入文档生成候选三级指标。一级指标和二级指标固定不变，只能生成三级指标。
固定二级指标及其一级归属：
{json.dumps(LEVEL2_TO_LEVEL1, ensure_ascii=False, indent=2)}

维度匹配结果：
{json.dumps((matching_result or {}), ensure_ascii=False)[:2000]}

输入文档摘录：
{context[:6000]}

请生成 1-5 个候选三级指标。level2 只能从以下列表选择：
{json.dumps(allowed_level2, ensure_ascii=False)}

JSON 格式：
{{
  "indicators": [
    {{
      "level2": "固定二级指标名称",
      "level3": "三级指标名称",
      "definition": "三级指标定义",
      "positive_example": "正例",
      "negative_example": "反例",
      "source_evidence": "来自输入文档的依据或摘要"
    }}
  ]
}}"""

        try:
            response = await llm_invoke(LEVEL3_SYSTEM_PROMPT, user_prompt, temperature=0.5)
        except Exception as exc:
            return {"items": [], "llm_fallback": True, "llm_error": str(exc)}

        parsed = self._extract_first_json_object(response)
        if not parsed:
            return {"items": [], "llm_fallback": True, "llm_error": "llm_json_parse_failed"}

        normalized_items = [
            item
            for item in (
                self._normalize_generated_level3_item(raw, matching_result)
                for raw in parsed.get("indicators", [])
            )
            if item
        ]
        return {"items": normalized_items, "llm_fallback": False, "llm_error": ""}

    async def run(
        self,
        dimension_data: Dict,
        context_texts: Optional[List[str]] = None,
        callback=None,
        force_generate: bool = False,
        matching_result: Optional[Dict] = None,
        mining_demand: str = "level3",
        **_: Dict,
    ) -> List[Dict]:
        """Generate candidate indicators according to the requested level."""
        if callback:
            await callback("IndicatorGeneratorAgent", "running", "开始生成候选指标...")

        context = " ".join(context_texts or []).strip()
        if not context and force_generate:
            raise RuntimeError("缺少可用于生成候选指标的输入文本")
        if not context:
            return [dict(item) for item in PREDEFINED_INDICATORS] if mining_demand == "level3" else []

        generation = {"items": [], "llm_fallback": False, "llm_error": ""}
        if mining_demand == "level1":
            generation = await self.generate_level1_indicators(context)
        elif mining_demand == "level2":
            generation = await self.generate_level2_indicators(context)
        else:
            generation = await self.generate_level3_indicators(context, matching_result)

        if generation.get("llm_error"):
            raise RuntimeError(f"LLM 生成候选指标失败: {generation.get('llm_error')}")

        items = generation.get("items", [])
        if callback:
            await callback(
                "IndicatorGeneratorAgent",
                "completed",
                f"生成完成：候选 {len(items)} 个，LLM 降级={bool(generation.get('llm_fallback'))}",
            )

        if mining_demand == "level3":
            return [dict(item) for item in PREDEFINED_INDICATORS] + items
        return items
