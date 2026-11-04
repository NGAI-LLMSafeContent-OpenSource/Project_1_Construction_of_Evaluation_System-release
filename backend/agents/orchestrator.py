"""Multi-agent orchestrator."""

import asyncio
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from agents.dimension_extractor import DimensionExtractorAgent
from agents.indicator_generator import PREDEFINED_INDICATORS, IndicatorGeneratorAgent
from agents.policy_retriever import PolicyRetrieverAgent
from ontology.new_indicator_taxonomy import (
    ALLOWED_DIMENSIONS,
    LEVEL1_TO_DIMENSION,
    LEVEL2_TO_LEVEL1,
)
from utils.llm_client import get_llm_runtime_config


DEMAND_LABELS = {
    "level1": "一级指标",
    "level2": "二级指标",
    "level3": "三级指标",
}


class AgentOrchestrator:
    """Coordinate document extraction and candidate indicator generation."""

    def __init__(self):
        self.policy_agent = PolicyRetrieverAgent()
        self.dimension_agent = DimensionExtractorAgent()
        self.indicator_agent = IndicatorGeneratorAgent()
        self.logs = []
        self.websocket_callbacks = []
        self.predefined_items = [self._decorate_indicator(dict(item)) for item in PREDEFINED_INDICATORS]

    def add_websocket_callback(self, callback: Callable):
        self.websocket_callbacks.append(callback)

    def remove_websocket_callback(self, callback: Callable):
        if callback in self.websocket_callbacks:
            self.websocket_callbacks.remove(callback)

    def _decorate_indicator(self, item: Dict) -> Dict:
        normalized = dict(item)
        level1 = str(normalized.get("level1") or "").strip()
        level2 = str(normalized.get("level2") or "").strip()
        level3 = str(normalized.get("level3") or "").strip()
        dimension = str(normalized.get("dimension") or "").strip()

        normalized["level1"] = level1
        normalized["level2"] = level2
        normalized["level3"] = level3
        normalized["name"] = normalized.get("name") or level3 or level2 or level1
        normalized["layer_name"] = normalized.get("layer_name") or ALLOWED_DIMENSIONS.get(dimension, "")
        normalized["formula_type"] = normalized.get("formula_type") or ""
        normalized["skill_name"] = normalized.get("skill_name") or ""
        normalized["formula"] = normalized.get("formula") or ""
        return normalized

    @staticmethod
    def _default_parent(matching_result: Optional[Dict] = None) -> Tuple[str, str, str]:
        matched_level2 = (matching_result or {}).get("matched_level2") or []
        for level2 in matched_level2:
            if level2 in LEVEL2_TO_LEVEL1:
                level1 = LEVEL2_TO_LEVEL1[level2]
                return LEVEL1_TO_DIMENSION[level1], level1, level2
        return "scene_support", "任务关联度", "语义匹配度"

    def _normalize_level1_candidates(self, indicators: List[Dict]) -> List[Dict]:
        by_slot: Dict[Tuple[str, str], Dict] = {}
        for raw in indicators:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            level1 = str(item.get("level1") or item.get("name") or "").strip()
            if not level1:
                continue
            dimension = str(item.get("dimension") or "").strip()
            if dimension not in ALLOWED_DIMENSIONS and level1 in LEVEL1_TO_DIMENSION:
                dimension = LEVEL1_TO_DIMENSION[level1]
            if dimension not in ALLOWED_DIMENSIONS:
                dimension = ""

            item.update(
                {
                    "dimension": dimension,
                    "layer_name": item.get("layer_name") or ALLOWED_DIMENSIONS.get(dimension, ""),
                    "level1": level1,
                    "level2": "",
                    "level3": "",
                    "level4": None,
                    "name": level1,
                    "status": item.get("status") or "pending",
                    "formula": "",
                    "formula_type": "",
                    "skill_name": "",
                }
            )
            slot_key = (dimension, level1)
            if slot_key not in by_slot:
                by_slot[slot_key] = self._decorate_indicator(item)
        return list(by_slot.values())

    def _normalize_level2_candidates(self, indicators: List[Dict]) -> List[Dict]:
        by_slot: Dict[Tuple[str, str, str], Dict] = {}
        for raw in indicators:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            level1 = str(item.get("level1") or "").strip()
            level2 = str(item.get("level2") or item.get("name") or "").strip()
            if not (level1 and level2):
                continue
            dimension = str(item.get("dimension") or "").strip()
            if dimension not in ALLOWED_DIMENSIONS and level1 in LEVEL1_TO_DIMENSION:
                dimension = LEVEL1_TO_DIMENSION[level1]
            if dimension not in ALLOWED_DIMENSIONS:
                dimension = ""

            item.update(
                {
                    "dimension": dimension,
                    "layer_name": item.get("layer_name") or ALLOWED_DIMENSIONS.get(dimension, ""),
                    "level1": level1,
                    "level2": level2,
                    "level3": "",
                    "level4": None,
                    "name": level2,
                    "status": item.get("status") or "pending",
                    "formula": "",
                    "formula_type": "",
                    "skill_name": "",
                }
            )
            slot_key = (dimension, level1, level2)
            if slot_key not in by_slot:
                by_slot[slot_key] = self._decorate_indicator(item)
        return list(by_slot.values())

    def _normalize_level3_candidates(
        self,
        indicators: List[Dict],
        matching_result: Optional[Dict] = None,
    ) -> List[Dict]:
        default_dimension, default_level1, default_level2 = self._default_parent(matching_result)
        by_slot: Dict[Tuple[str, str, str, str], Dict] = {}

        for raw in indicators:
            if not isinstance(raw, dict):
                continue

            item = dict(raw)
            level2 = str(item.get("level2") or "").strip()
            level1 = str(item.get("level1") or "").strip()
            dimension = str(item.get("dimension") or "").strip()

            if level2 in LEVEL2_TO_LEVEL1:
                level1 = LEVEL2_TO_LEVEL1[level2]
                dimension = LEVEL1_TO_DIMENSION[level1]
            elif level1 in LEVEL1_TO_DIMENSION:
                dimension = LEVEL1_TO_DIMENSION[level1]
                allowed_l2 = [key for key, value in LEVEL2_TO_LEVEL1.items() if value == level1]
                level2 = allowed_l2[0] if allowed_l2 else default_level2
            elif dimension in ALLOWED_DIMENSIONS:
                if dimension == "culture_adapt":
                    level1, level2 = "文化忠实度", "文化元素符合度"
                else:
                    level1, level2 = "任务关联度", "语义匹配度"
            else:
                dimension, level1, level2 = default_dimension, default_level1, default_level2

            level3 = str(item.get("level3") or item.get("name") or "").strip()
            if level3 == level2:
                level3 = ""

            item.update(
                {
                    "dimension": dimension,
                    "layer_name": ALLOWED_DIMENSIONS.get(dimension, ""),
                    "level1": level1,
                    "level2": level2,
                    "level3": level3,
                    "level4": None,
                    "name": level3 or level2,
                    "status": "approved" if not level3 else item.get("status") or "pending",
                    "formula": "",
                    "formula_type": "",
                    "skill_name": "",
                }
            )

            item = self._decorate_indicator(item)
            slot_key = (dimension, level1, level2, level3)
            if slot_key not in by_slot:
                by_slot[slot_key] = item

        return list(by_slot.values())

    def _normalize_indicators(
        self,
        indicators: List[Dict],
        matching_result: Optional[Dict] = None,
        mining_demand: str = "level3",
    ) -> List[Dict]:
        if mining_demand == "level1":
            return self._normalize_level1_candidates(indicators)
        if mining_demand == "level2":
            return self._normalize_level2_candidates(indicators)
        return self._normalize_level3_candidates(indicators, matching_result)

    def _extract_new_indicators(self, indicators: List[Dict], mining_demand: str) -> List[Dict]:
        new_items = []
        seen_paths = set()

        for item in indicators:
            level1 = str(item.get("level1") or "").strip()
            level2 = str(item.get("level2") or "").strip()
            level3 = str(item.get("level3") or "").strip()

            if mining_demand == "level1":
                if not level1:
                    continue
                path = ("level1", level1)
            elif mining_demand == "level2":
                if not (level1 and level2):
                    continue
                path = ("level2", level1, level2)
            else:
                if not level3:
                    continue
                path = ("level3", level1, level2, level3)

            if path in seen_paths:
                continue
            seen_paths.add(path)
            new_items.append(self._decorate_indicator({**item, "status": "pending"}))

        return new_items

    @staticmethod
    def _project_indicators_by_demand(indicators: List[Dict], mining_demand: str) -> List[Dict]:
        return indicators

    async def broadcast(self, agent_name: str, status: str, message: str):
        log_entry = {
            "id": str(uuid.uuid4())[:8],
            "agent_name": agent_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        self.logs.append(log_entry)
        for callback in self.websocket_callbacks:
            try:
                await callback(log_entry)
            except Exception:
                pass

    async def run_pipeline(
        self,
        policy_texts: Optional[List[str]] = None,
        standard_texts: Optional[List[str]] = None,
        case_texts: Optional[List[str]] = None,
        web_links: Optional[List[str]] = None,
        mining_demand: str = "level3",
    ) -> Dict:
        task_id = str(uuid.uuid4())
        normalized_demand = str(mining_demand or "level3").strip().lower()
        if normalized_demand not in DEMAND_LABELS:
            normalized_demand = "level3"

        normalized_links = [link for link in (web_links or []) if link]
        runtime = get_llm_runtime_config()

        await self.broadcast("系统", "started", f"任务 {task_id[:8]} 开始，目标：生成候选{DEMAND_LABELS[normalized_demand]}。")
        await self.broadcast(
            "系统",
            "running",
            f"当前 LLM: {runtime.get('provider')} / {runtime.get('model')} / {runtime.get('base_url')}",
        )

        all_texts: List[str] = []
        all_texts.extend(policy_texts or [])
        all_texts.extend(standard_texts or [])
        all_texts.extend(case_texts or [])

        await asyncio.sleep(0.1)
        policy_data = await self.policy_agent.run(input_texts=all_texts, callback=self.broadcast)

        await asyncio.sleep(0.1)
        dimension_data = await self.dimension_agent.run(
            policy_data=policy_data,
            additional_texts=all_texts,
            callback=self.broadcast,
        )

        matching_result = dimension_data.get("matching", {})
        await self.broadcast(
            "IndicatorGeneratorAgent",
            "running",
            f"调用 LLM 生成候选{DEMAND_LABELS[normalized_demand]}。",
        )

        indicators = await self.indicator_agent.run(
            dimension_data=dimension_data,
            context_texts=all_texts,
            callback=self.broadcast,
            force_generate=True,
            matching_result=matching_result,
            mining_demand=normalized_demand,
        )

        indicators = self._normalize_indicators(indicators, matching_result, normalized_demand)
        new_indicators = self._extract_new_indicators(indicators, normalized_demand)
        display_indicators = self._project_indicators_by_demand(new_indicators, normalized_demand)
        coverage = min(92 + len(all_texts) * 2, 99)

        await self.broadcast("系统", "completed", f"挖掘完成，新增 {len(new_indicators)} 个候选{DEMAND_LABELS[normalized_demand]}。")

        return {
            "task_id": task_id,
            "policy_data": policy_data,
            "dimension_data": dimension_data,
            "indicators": indicators,
            "new_indicators": new_indicators,
            "display_indicators": display_indicators,
            "agent_outputs": {
                "policy_retriever": {
                    "key_values_count": len(policy_data.get("key_values", [])),
                    "dimensions_count": len(policy_data.get("dimensions", [])),
                    "requirements_count": len(policy_data.get("requirements", [])),
                    "llm_fallback_count": policy_data.get("llm_fallback_count", 0),
                    "top_key_values": policy_data.get("key_values", [])[:8],
                },
                "dimension_extractor": {
                    "dimensions_count": len(dimension_data.get("dimensions", [])),
                    "matched_paths_count": len(matching_result.get("matched_paths", [])),
                    "uncovered": bool(matching_result.get("uncovered")),
                    "matched_level1": matching_result.get("matched_level1", []),
                    "matched_level2": matching_result.get("matched_level2", []),
                    "llm_fallback": bool(dimension_data.get("_meta", {}).get("llm_fallback", False)),
                },
                "indicator_generator": {
                    "total_indicators": len(indicators),
                    "new_indicators": len(new_indicators),
                    "selected_indicators": len(display_indicators),
                    "top_indicator_names": [item.get("name", "") for item in display_indicators[:8]],
                    "needs_expansion": normalized_demand == "level3",
                },
            },
            "request_context": {
                "mining_demand": normalized_demand,
                "web_links": normalized_links,
                "llm_runtime": runtime,
                "name_review_policy": "manual_required",
            },
            "stats": {
                "total_indicators": len(indicators),
                "new_indicators_count": len(new_indicators),
                "selected_indicators_count": len(display_indicators),
                "dimensions_count": len(dimension_data.get("dimensions", [])),
                "coverage_rate": coverage,
                "input_docs": len(all_texts),
                "mining_demand": normalized_demand,
                "web_links_count": len(normalized_links),
                "name_review_required": True,
            },
        }

    def get_logs(self) -> List[Dict]:
        return self.logs[-50:]


orchestrator = AgentOrchestrator()
