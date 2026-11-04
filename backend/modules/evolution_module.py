"""
评估标准自主演化算法
功能：基于新增语料、政策更新，自动触发案例库的增量更新
"""
import json
import re
from typing import List, Dict
from datetime import datetime
try:
    from utils.llm_client import llm_invoke
except ImportError:
    from backend.utils.llm_client import llm_invoke
from utils.vector_store import vector_store

class EvolutionModule:
    """评估标准自主演化模块"""
    
    def __init__(self):
        self.update_history = []
    
    async def analyze_new_content(self, new_content: str, content_type: str = "policy") -> Dict:
        """分析新内容，判断是否需要更新指标"""
        system_prompt = """你是数据评估标准演化专家，负责分析新政策/语料对现有评估指标体系的影响。
        请判断新内容是否需要触发指标更新，并给出具体建议。
        严格按JSON格式输出。"""
        
        user_prompt = f"""分析以下新增内容对数据评估指标体系的影响：

内容类型：{content_type}
新增内容：{new_content[:1000]}

请输出分析结果（JSON格式）：
{{
    "needs_update": true/false,
    "update_type": "add/modify/expand",
    "affected_dimensions": ["受影响的维度列表"],
    "suggestions": ["具体更新建议列表"],
    "new_cases": [
        {{
            "title": "案例标题",
            "content": "案例内容摘要",
            "dimension": "对应维度",
            "indicator_name": "关联指标"
        }}
    ]
}}"""
        
        response = await llm_invoke(system_prompt, user_prompt, temperature=0.4)
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "needs_update": False,
            "update_type": "none",
            "affected_dimensions": [],
            "suggestions": [],
            "new_cases": []
        }
    
    async def generate_case(self, indicator_name: str, dimension: str, context: str = "") -> Dict:
        """为指标生成典型案例"""
        system_prompt = """你是数据质量评估案例专家，能够为评估指标设计典型正反面案例。
        案例要真实、具体、有代表性，符合中国国情。"""
        
        user_prompt = f"""为以下评估指标生成典型案例：

指标名称：{indicator_name}
所属维度：{dimension}
背景信息：{context[:300] if context else '无'}

请生成一个正面案例和一个反面案例（JSON格式）：
{{
    "positive_case": {{
        "title": "案例标题",
        "content": "案例详细描述（200字以内）",
        "tags": ["标签1", "标签2"]
    }},
    "negative_case": {{
        "title": "案例标题",
        "content": "案例详细描述（200字以内）",
        "tags": ["标签1", "标签2"]
    }}
}}"""
        
        response = await llm_invoke(system_prompt, user_prompt, temperature=0.6)
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "positive_case": {
                "title": f"{indicator_name}-正面案例",
                "content": f"该案例展示了{indicator_name}指标的正面示范，符合相关标准要求。",
                "tags": [dimension, indicator_name, "正面"]
            },
            "negative_case": {
                "title": f"{indicator_name}-反面案例",
                "content": f"该案例展示了{indicator_name}指标的反面问题，需要改进。",
                "tags": [dimension, indicator_name, "反面"]
            }
        }
    
    async def trigger_incremental_update(self, new_content: str, content_type: str) -> Dict:
        """触发增量更新"""
        analysis = await self.analyze_new_content(new_content, content_type)
        
        update_record = {
            "timestamp": datetime.now().isoformat(),
            "content_type": content_type,
            "analysis": analysis,
            "triggered": analysis.get("needs_update", False)
        }
        self.update_history.append(update_record)
        
        # 添加到向量库
        if len(new_content.strip()) > 10:
            vector_store.add_policy(
                doc_id=f"evolution_{len(self.update_history)}",
                content=new_content,
                metadata={
                    "title": f"演化更新内容_{content_type}",
                    "doc_type": content_type,
                    "source_url": "用户上传"
                }
            )
        
        return {
            "update_triggered": analysis.get("needs_update", False),
            "affected_dimensions": analysis.get("affected_dimensions", []),
            "suggestions": analysis.get("suggestions", []),
            "new_cases": analysis.get("new_cases", []),
            "update_record": update_record
        }
    
    def get_update_history(self) -> List[Dict]:
        """获取更新历史"""
        return self.update_history

evolution_module = EvolutionModule()
