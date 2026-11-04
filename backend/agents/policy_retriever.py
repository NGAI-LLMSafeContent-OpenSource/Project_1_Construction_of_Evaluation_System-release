#update file
"""
政策检索智能体
功能：自动抓取和解析政策文档，提取关键信息
"""
import json
import os
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, UnicodeDammit
from sqlalchemy.ext.asyncio import AsyncSession

from modules.policy_document_service import policy_document_service
try:
    from utils.llm_client import llm_invoke
except ImportError:
    from backend.utils.llm_client import llm_invoke
from utils.vector_store import vector_store

SYSTEM_PROMPT = """你是一个专业的政策文档分析专家，专注于：
1. 分析中国社会主义核心价值观相关政策文件
2. 提取政策中的关键价值观维度和评估要求
3. 识别数据治理、AI对齐相关标准中的评估指标
请以结构化JSON格式输出分析结果。"""

# 预置的政策知识库（当网络抓取不可用时使用）
BUILTIN_POLICIES = [
    {
        "id": "policy_001",
        "title": "社会主义核心价值观（24字）",
        "content": """社会主义核心价值观包含三个层面：
        国家层面：富强、民主、文明、和谐
        社会层面：自由、平等、公正、法治  
        公民层面：爱国、敬业、诚信、友善
        这是当代中国精神的集中体现，凝结着全体人民共同的价值追求。""",
        "doc_type": "policy",
        "source_url": "http://www.xinhuanet.com/politics/2012-11/19/c_113722455.htm"
    },
    {
        "id": "policy_002", 
        "title": "新时代公民道德建设实施纲要",
        "content": """坚持以社会主义核心价值观为引领，推进公民道德建设工程。
        重点内容：
        1. 筑牢理想信念之基：坚定对马克思主义的信仰，坚定对中国特色社会主义的信念
        2. 培育和践行社会主义核心价值观：国家、社会、个人三个层面
        3. 传承中华传统美德：重家庭家教家风、注重个人品德修养
        4. 弘扬民族精神和时代精神：爱国主义是民族精神的核心
        5. 深化网络空间道德建设：维护网络空间清朗""",
        "doc_type": "policy",
        "source_url": "http://www.gov.cn/zhengce/2019-10/27/content_5445556.htm"
    },
    {
        "id": "standard_001",
        "title": "数据管理能力成熟度评估模型（DCMM）",
        "content": """数据管理能力评估框架包含8个能力域：
        1. 数据战略：数据战略规划、实施、评估
        2. 数据治理：数据治理组织、制度、流程
        3. 数据架构：数据模型、数据分布、数据集成
        4. 数据应用：数据分析、数据服务、数据质量应用
        5. 数据安全：数据安全策略、数据安全管理、数据安全审计
        6. 数据质量：数据质量需求、数据质量监控、数据质量提升
        7. 数据标准：数据标准管理、数据标准应用
        8. 数据生存周期：数据需求、数据设计和开发、数据运维""",
        "doc_type": "standard",
        "source_url": "https://std.samr.gov.cn/"
    },
    {
        "id": "standard_002",
        "title": "人工智能 大模型语料数据处理规范（草案）",
        "content": """大模型语料数据质量评估维度：
        1. 数据合规性：版权合规、隐私保护、内容安全
        2. 数据多样性：领域分布、语种分布、时间分布
        3. 数据质量：准确性、完整性、一致性、时效性
        4. 数据价值密度：信息密度、知识含量、推理深度
        5. 安全过滤：有害内容过滤、偏见检测、事实核查
        评估指标应可量化、可复现、可解释。""",
        "doc_type": "standard",
        "source_url": "https://www.tc260.org.cn/"
    },
    {
        "id": "case_001",
        "title": "典型案例：社会主义核心价值观融入AI数据集建设",
        "content": """案例描述：某科研机构在构建中文大模型训练数据集时，
        系统性地融入社会主义核心价值观评估维度：
        1. 建立价值观关键词词典，包含正向词汇3000+、负向词汇2000+
        2. 设计三级评估指标体系，覆盖国家、社会、公民三个层面
        3. 引入人工智能辅助标注，结合专家复核机制
        4. 实现指标体系动态更新，每季度根据最新政策调整
        效果：数据集价值观对齐率从67%提升至94%""",
        "doc_type": "case",
        "source_url": "内部案例"
    }
]

class PolicyRetrieverAgent:
    """政策检索智能体"""
    
    def __init__(self):
        self.agent_name = "PolicyRetrieverAgent"
        self.crawl_timeout_seconds = float(os.getenv("POLICY_CRAWL_TIMEOUT_SECONDS", "18"))
        self.crawl_min_relevance = float(os.getenv("POLICY_CRAWL_MIN_RELEVANCE", "0.35"))
        self.crawl_user_agent = os.getenv(
            "POLICY_CRAWL_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        # Do not upsert built-in legacy policy snippets at application startup.
        # It can trigger embedding model downloads and also reintroduce obsolete
        # value-core taxonomy content. Uploaded/link documents are handled at run time.
        self.source_configs = [
            {
                "site": "gov",
                "doc_type": "policy",
                "list_urls": [
                    "https://www.gov.cn/zhengce/",
                    "https://www.gov.cn/zhengce/zuixin/",
                ],
            },
            {
                "site": "cac",
                "doc_type": "policy",
                "list_urls": [
                    "https://www.cac.gov.cn/",
                ],
            },
            {
                "site": "samr",
                "doc_type": "standard",
                "list_urls": [
                    "https://std.samr.gov.cn/",
                ],
            },
            {
                "site": "tc260",
                "doc_type": "standard",
                "list_urls": [
                    "https://www.tc260.org.cn/",
                ],
            },
        ]
        self.last_crawl_status = {
            "last_run_at": None,
            "status": "idle",
            "saved": 0,
            "duplicates": 0,
            "skipped_low_relevance": 0,
            "errors": [],
        }
    
    def _init_builtin_policies(self):
        """初始化内置政策到向量库"""
        for policy in BUILTIN_POLICIES:
            vector_store.add_policy(
                doc_id=policy["id"],
                content=policy["content"],
                metadata={
                    "title": policy["title"],
                    "doc_type": policy["doc_type"],
                    "source_url": policy["source_url"]
                }
            )
    
    async def retrieve_from_text(self, text: str) -> Dict:
        """从上传的文本中提取政策信息"""
        system_prompt = SYSTEM_PROMPT
        llm_error = ""
        user_prompt = f"""请分析以下政策/标准文档，提取其中与数据评估相关的关键信息：

文档内容：
{text[:3000]}

请以如下JSON格式输出：
{{
    "key_values": ["提取的核心价值词汇列表"],
    "dimensions": ["评估维度列表"],
    "requirements": ["具体评估要求列表"],
    "keywords": ["关键词列表"]
}}"""
        
        try:
            response = await llm_invoke(system_prompt, user_prompt, temperature=0.3)
        except Exception as exc:
            llm_error = str(exc)
            response = ""
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                parsed["llm_fallback"] = False
                parsed["llm_error"] = ""
                return parsed
        except:
            llm_error = llm_error or "llm_json_parse_failed"
        
        return {
            "key_values": ["文化忠实度", "伦理敏感度", "语义稀缺度", "任务关联度"],
            "dimensions": ["文化适配层", "场景支撑层"],
            "requirements": ["指标可量化", "覆盖完整", "来源可溯"],
            "keywords": ["文化适配", "场景支撑", "数据评估", "指标体系"],
            "llm_fallback": True,
            "llm_error": llm_error,
        }

    def get_last_crawl_status(self) -> Dict:
        """返回最近一次抓取状态。"""
        return self.last_crawl_status

    def _extract_candidate_links(self, html: str, base_url: str) -> List[Dict]:
        """从列表页提取候选链接。"""
        soup = BeautifulSoup(html, "html.parser")
        candidates: List[Dict] = []
        for a in soup.find_all("a", href=True):
            title = (a.get_text() or "").strip()
            if len(title) < 8:
                continue
            raw_href = a.get("href", "")
            href = raw_href if isinstance(raw_href, str) else ""
            href = href.strip()
            full_url = href if href.startswith("http") else urljoin(base_url, href)
            candidates.append({"title": title[:200], "url": full_url})

        return candidates

    @staticmethod
    def _decode_response_text(resp: httpx.Response) -> str:
        """Decode response bytes with robust charset fallback to reduce mojibake."""
        if not resp.content:
            return ""
        decoded = UnicodeDammit(resp.content)
        if decoded.unicode_markup:
            return decoded.unicode_markup
        try:
            return resp.content.decode("utf-8", errors="ignore")
        except Exception:
            return resp.text

    async def _fetch_article_content(self, client: httpx.AsyncClient, url: str) -> str:
        """抓取详情页正文，抓不到时返回空字符串。"""
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            html = self._decode_response_text(resp)
            soup = BeautifulSoup(html, "html.parser")
            paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            text = "\n".join([p for p in paragraphs if p])
            return text[:6000]
        except Exception:
            return ""

    async def crawl_latest_documents(
        self,
        db: AsyncSession,
        callback=None,
        max_docs_per_site: int = 10,
    ) -> Dict:
        """
        自动抓取最新政策/标准文档并入库。
        仅保留与社会主义核心价值观、数据治理、AI对齐相关内容。
        """
        crawl_batch_id = str(uuid.uuid4())[:12]
        status = {
            "last_run_at": datetime.utcnow().isoformat(),
            "status": "running",
            "saved": 0,
            "duplicates": 0,
            "skipped_low_relevance": 0,
            "errors": [],
            "crawl_batch_id": crawl_batch_id,
        }
        self.last_crawl_status = status

        if callback:
            await callback(self.agent_name, "running", "开始自动抓取政策与标准文档...")

        headers = {
            "User-Agent": self.crawl_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }

        async with httpx.AsyncClient(
            timeout=self.crawl_timeout_seconds,
            follow_redirects=True,
            headers=headers,
        ) as client:
            for config in self.source_configs:
                site = config["site"]
                doc_type = config["doc_type"]
                for list_url in config["list_urls"]:
                    try:
                        resp = await client.get(list_url)
                        resp.raise_for_status()
                        list_html = self._decode_response_text(resp)
                        candidates = self._extract_candidate_links(list_html, list_url)

                        handled = 0
                        for c in candidates:
                            if handled >= max_docs_per_site:
                                break

                            title = c["title"]
                            url = c["url"]
                            if not url.startswith("http"):
                                continue

                            # 先抓正文，抓不到时退化到标题。
                            content = await self._fetch_article_content(client, url)
                            if not content:
                                content = title

                            save_result = await policy_document_service.save_document(
                                db,
                                title=title,
                                content=content,
                                doc_type=doc_type,
                                source_site=site,
                                source_url=url,
                                crawl_batch_id=crawl_batch_id,
                                min_relevance=self.crawl_min_relevance,
                            )

                            if save_result.get("saved"):
                                status["saved"] += 1
                            elif save_result.get("duplicated"):
                                status["duplicates"] += 1
                            elif save_result.get("reason") == "low_relevance":
                                status["skipped_low_relevance"] += 1

                            handled += 1
                    except Exception as exc:
                        status["errors"].append(f"{site}:{list_url} -> {str(exc)[:120]}")

        status["status"] = "completed"
        self.last_crawl_status = status

        if callback:
            await callback(
                self.agent_name,
                "completed",
                f"抓取完成：新增 {status['saved']}，重复 {status['duplicates']}，低相关过滤 {status['skipped_low_relevance']}",
            )

        return status
    
    async def search_relevant_policies(self, query: str) -> List[Dict]:
        """检索相关政策"""
        results = vector_store.search_policy(query, n_results=3)
        
        policies = []
        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []
        first_docs = documents[0] if len(documents) > 0 and documents[0] is not None else []
        first_metas = metadatas[0] if len(metadatas) > 0 and metadatas[0] is not None else []

        if results and results.get("documents"):
            for i, doc in enumerate(first_docs):
                metadata = first_metas[i] if i < len(first_metas) and first_metas[i] is not None else {}
                policies.append({
                    "content": doc,
                    "title": metadata.get("title", "未知文档"),
                    "doc_type": metadata.get("doc_type", "unknown"),
                    "source_url": metadata.get("source_url", "")
                })
        
        return policies
    
    async def run(self, input_texts: List[str], callback=None) -> Dict:
        """主运行函数"""
        if callback:
            await callback("PolicyRetrieverAgent", "running", "开始分析输入文档...")
        
        all_key_values = set()
        all_dimensions = set()
        all_requirements = []
        llm_fallback_count = 0
        
        # 默认加载内置政策知识
        all_key_values.update(["文化忠实度", "伦理敏感度", "语义稀缺度", "任务关联度"])
        all_dimensions.update(["文化适配层", "场景支撑层"])
        
        # 处理输入文本
        for text in input_texts:
            if len(text.strip()) > 10:
                result = await self.retrieve_from_text(text)
                all_key_values.update(result.get("key_values", []))
                all_dimensions.update(result.get("dimensions", []))
                all_requirements.extend(result.get("requirements", []))
                if result.get("llm_fallback"):
                    llm_fallback_count += 1
        
        # 存储到向量库
        if input_texts:
            for i, text in enumerate(input_texts):
                if len(text.strip()) > 10:
                    try:
                        vector_store.add_policy(
                            doc_id=f"user_input_{i}",
                            content=text,
                            metadata={"title": f"用户输入文档{i+1}", "doc_type": "user_input"}
                        )
                    except Exception:
                        pass
        
        if callback:
            await callback("PolicyRetrieverAgent", "completed", 
                         f"成功提取 {len(all_key_values)} 个关键价值词汇，{len(all_dimensions)} 个评估维度，"
                         f"LLM降级={llm_fallback_count}")
        
        return {
            "key_values": list(all_key_values),
            "dimensions": list(all_dimensions),
            "requirements": all_requirements,
            "builtin_policies_count": len(BUILTIN_POLICIES),
            "llm_fallback_count": llm_fallback_count,
        }
