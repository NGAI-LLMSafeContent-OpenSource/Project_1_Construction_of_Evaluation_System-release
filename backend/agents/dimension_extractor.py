"""Dimension extraction agent for the fixed indicator structure."""

import os
import re
from typing import Dict, List, Optional, Set

try:
    from agents.indicator_generator import PREDEFINED_INDICATORS
    from ontology.new_indicator_taxonomy import ALLOWED_DIMENSIONS, LEVEL1_DEFINITIONS, LEVEL2_TO_LEVEL1
except ImportError:
    from backend.agents.indicator_generator import PREDEFINED_INDICATORS
    from backend.ontology.new_indicator_taxonomy import ALLOWED_DIMENSIONS, LEVEL1_DEFINITIONS, LEVEL2_TO_LEVEL1


class DimensionExtractorAgent:
    """Match input text against the fixed taxonomy without inventing nodes."""

    def __init__(self):
        self.agent_name = "DimensionExtractorAgent"

    @staticmethod
    def _safe_float_env(name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    @staticmethod
    def _clip(value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip()).lower()

    @staticmethod
    def _tokenize_keywords(text: str) -> Set[str]:
        if not text:
            return set()
        tokens = set()
        for chunk in re.split(r"[\s,，。；;：:、.!?？（）()\[\]{}\-_/]+", text):
            part = chunk.strip()
            if len(part) >= 2 and not part.isdigit():
                tokens.add(part)
        return tokens

    def _indicator_keywords(self, indicator: Dict) -> Set[str]:
        seeds = [
            indicator.get("name", ""),
            indicator.get("layer_name", ""),
            indicator.get("level1", ""),
            indicator.get("level2", ""),
            indicator.get("definition", ""),
            indicator.get("positive_example", ""),
            indicator.get("negative_example", ""),
            indicator.get("source", ""),
        ]
        keywords: Set[str] = set()
        for seed in seeds:
            keywords.update(self._tokenize_keywords(seed))
        return {k for k in keywords if len(k) <= 24}

    def _score_indicator(self, text: str, indicator: Dict) -> Dict:
        normalized_text = self._normalize_text(text)
        keywords = self._indicator_keywords(indicator)
        if not keywords:
            return {"confidence": 0.0, "hits": []}

        hits = [k for k in keywords if k and k.lower() in normalized_text]
        coverage = len(hits) / max(3, min(10, len(keywords)))
        weighted_bonus = 0.0
        for field, weight in (("level1", 0.06), ("level2", 0.12), ("name", 0.08)):
            value = str(indicator.get(field, "")).strip().lower()
            if value and value in normalized_text:
                weighted_bonus += weight

        return {"confidence": round(min(1.0, coverage + weighted_bonus), 4), "hits": hits[:8]}

    def match_indicator_paths(
        self,
        input_texts: List[str],
        confidence_threshold: float,
        top_k: int = 12,
    ) -> Dict:
        full_text = "\n".join([t.strip() for t in input_texts if t and t.strip()])
        if len(full_text) < 10:
            return {
                "confidence_threshold": confidence_threshold,
                "max_confidence": 0.0,
                "matched_paths": [],
                "matched_level1": [],
                "matched_level2": [],
                "uncovered": True,
                "reason": "empty_or_too_short_input",
            }

        scored = []
        for item in PREDEFINED_INDICATORS:
            score = self._score_indicator(full_text, item)
            if score["confidence"] <= 0:
                continue
            scored.append(
                {
                    "dimension": item.get("dimension"),
                    "layer_name": item.get("layer_name"),
                    "level1": item.get("level1"),
                    "level2": item.get("level2"),
                    "confidence": score["confidence"],
                    "evidence_hits": score["hits"],
                }
            )

        scored.sort(key=lambda x: x["confidence"], reverse=True)
        max_confidence = scored[0]["confidence"] if scored else 0.0
        matched_paths = [x for x in scored if x["confidence"] >= confidence_threshold][:top_k]

        if not matched_paths and scored and max_confidence >= max(0.18, confidence_threshold - 0.05):
            matched_paths = scored[: min(3, top_k)]

        uncovered = not matched_paths
        return {
            "confidence_threshold": confidence_threshold,
            "max_confidence": max_confidence,
            "matched_paths": matched_paths,
            "matched_level1": sorted({x["level1"] for x in matched_paths}),
            "matched_level2": sorted({x["level2"] for x in matched_paths}),
            "uncovered": uncovered,
            "reason": "low_confidence_or_empty" if uncovered else "covered",
            "top_candidates": scored[:5],
        }

    def _get_predefined_structure(self) -> Dict:
        layers = {}
        for item in PREDEFINED_INDICATORS:
            layer_name = item["layer_name"]
            level1 = item["level1"]
            level2 = item["level2"]
            layer = layers.setdefault(
                layer_name,
                {
                    "name": layer_name,
                    "level": 1,
                    "description": "",
                    "sub_dimensions": {},
                },
            )
            sub = layer["sub_dimensions"].setdefault(
                level1,
                {
                    "name": level1,
                    "level": 2,
                    "description": LEVEL1_DEFINITIONS.get(level1, ""),
                    "indicators": [],
                },
            )
            if level2 in LEVEL2_TO_LEVEL1 and level2 not in sub["indicators"]:
                sub["indicators"].append(level2)

        dimensions = []
        for layer in layers.values():
            dimensions.append(
                {
                    **layer,
                    "sub_dimensions": list(layer["sub_dimensions"].values()),
                }
            )

        return {
            "dimensions": dimensions,
            "relationships": [
                {"source": ALLOWED_DIMENSIONS["culture_adapt"], "target": ALLOWED_DIMENSIONS["scene_support"], "relation": "支撑"},
            ],
        }

    async def run(self, policy_data: Dict, additional_texts: Optional[List[str]] = None, callback=None) -> Dict:
        if callback:
            await callback("DimensionExtractorAgent", "running", "开始匹配固定指标体系...")

        result = self._get_predefined_structure()
        threshold = self._clip(self._safe_float_env("DIMENSION_MATCH_THRESHOLD", 0.28), 0.18, 0.55)

        key_values = policy_data.get("key_values", []) if isinstance(policy_data, dict) else []
        requirements = policy_data.get("requirements", []) if isinstance(policy_data, dict) else []
        keywords = policy_data.get("keywords", []) if isinstance(policy_data, dict) else []

        matching_texts = list(additional_texts or [])
        if key_values:
            matching_texts.append(" ".join([str(x) for x in key_values[:40]]))
        if requirements:
            matching_texts.append(" ".join([str(x) for x in requirements[:20]]))
        if keywords:
            matching_texts.append(" ".join([str(x) for x in keywords[:40]]))

        matching = self.match_indicator_paths(matching_texts, threshold)
        result["matching"] = matching
        result["needs_indicator_expansion"] = True
        result["_meta"] = {"llm_fallback": False, "llm_error": ""}

        if callback:
            await callback(
                "DimensionExtractorAgent",
                "completed",
                f"固定体系匹配完成，命中 {len(matching.get('matched_paths', []))} 条二级指标路径。",
            )

        return result

