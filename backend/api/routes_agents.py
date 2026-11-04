"""Agent orchestration API routes."""

import html
import json
import re
import zipfile
from io import BytesIO
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup, UnicodeDammit
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import orchestrator
from models.schemas import PolicyDocument, get_db
from modules.review_module import review_module
from utils.llm_client import check_llm_health, get_llm_runtime_config

router = APIRouter(prefix="/api/agents", tags=["agents"])

MAX_UPLOAD_FILES = 30
MAX_LOOKUP_NAMES = 30
MINING_DEMAND_LABELS = {
    "level1": "一级指标",
    "level2": "二级指标",
    "level3": "三级指标",
}


class UploadedDocument(BaseModel):
    name: str
    content: str
    source_type: Optional[str] = "upload"


class MiningRequest(BaseModel):
    policy_texts: List[str] = Field(default_factory=list)
    standard_texts: List[str] = Field(default_factory=list)
    case_texts: List[str] = Field(default_factory=list)
    web_links: List[str] = Field(default_factory=list)
    lookup_names: List[str] = Field(default_factory=list)
    uploaded_documents: List[UploadedDocument] = Field(default_factory=list)
    mining_demand: Optional[str] = "level3"


def _build_indicator_dedupe_key(item: dict) -> str:
    level1 = str(item.get("level1") or "").strip()
    level2 = str(item.get("level2") or "").strip()
    level3 = str(item.get("level3") or "").strip()
    name = str(item.get("name") or "").strip()

    if level3:
        return f"l3::{level1}::{level2}::{level3}"
    if level2:
        return f"l2::{level1}::{level2}"
    if level1:
        return f"l1::{level1}"
    return f"name::{name}"


def _best_effort_decode(raw: bytes) -> str:
    if not raw:
        return ""

    decoded = UnicodeDammit(raw)
    if decoded.unicode_markup:
        return decoded.unicode_markup

    for encoding in ("utf-8", "gb18030", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue

    return raw.decode("utf-8", errors="ignore")


def _clean_text(text: str) -> str:
    cleaned = html.unescape(text or "")
    cleaned = re.sub(r"\r\n?", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _extract_text_from_docx(raw: bytes) -> str:
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        fragments = []
        for name in archive.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                xml_text = archive.read(name).decode("utf-8", errors="ignore")
                fragments.extend(re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml_text))
        return _clean_text(" ".join(fragments))


def _extract_text_from_pptx(raw: bytes) -> str:
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        fragments = []
        slide_names = sorted(
            name for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        for name in slide_names:
            xml_text = archive.read(name).decode("utf-8", errors="ignore")
            fragments.extend(re.findall(r"<a:t>(.*?)</a:t>", xml_text))
        return _clean_text(" ".join(fragments))


def _extract_text_from_xlsx(raw: bytes) -> str:
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        fragments = []
        shared_strings: List[str] = []

        if "xl/sharedStrings.xml" in archive.namelist():
            shared_xml = archive.read("xl/sharedStrings.xml").decode("utf-8", errors="ignore")
            shared_strings = re.findall(r"<t[^>]*>(.*?)</t>", shared_xml)

        for name in archive.namelist():
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue
            xml_text = archive.read(name).decode("utf-8", errors="ignore")
            for value in re.findall(r"<v>(.*?)</v>", xml_text):
                if value.isdigit():
                    shared_index = int(value)
                    if 0 <= shared_index < len(shared_strings):
                        fragments.append(shared_strings[shared_index])
                        continue
                fragments.append(value)

        return _clean_text(" ".join(fragments))


def _extract_html_text(raw: bytes) -> str:
    soup = BeautifulSoup(_best_effort_decode(raw), "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    parts = [node.get_text(" ", strip=True) for node in soup.find_all(["h1", "h2", "h3", "p", "li"])]
    return _clean_text("\n".join([part for part in [title, *parts] if part]))


def _extract_text_from_bytes(filename: str, raw: bytes, content_type: str = "") -> str:
    lowered_name = (filename or "").lower()
    lowered_type = (content_type or "").lower()

    if lowered_name.endswith(".docx"):
        return _extract_text_from_docx(raw)
    if lowered_name.endswith(".pptx"):
        return _extract_text_from_pptx(raw)
    if lowered_name.endswith(".xlsx"):
        return _extract_text_from_xlsx(raw)
    if lowered_name.endswith((".html", ".htm")) or "text/html" in lowered_type:
        return _extract_html_text(raw)

    text = _best_effort_decode(raw)
    if "<html" in text.lower():
        return _extract_html_text(raw)
    return _clean_text(text)


async def _parse_upload_file(upload: UploadFile) -> dict:
    raw = await upload.read()
    content = _extract_text_from_bytes(upload.filename or "upload.txt", raw, upload.content_type or "")
    if len(content) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"文件 {upload.filename or 'unknown'} 解析后内容过短，暂不支持该格式",
        )

    return {
        "name": upload.filename or "未命名文件",
        "content": content[:20000],
        "source_type": "upload",
        "size": len(raw),
    }


async def _fetch_url_document(url: str) -> Optional[dict]:
    normalized = (url or "").strip()
    if not normalized:
        return None
    if not re.match(r"^https?://", normalized, flags=re.IGNORECASE):
        normalized = f"https://{normalized}"

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(normalized)
        response.raise_for_status()
        content = _extract_text_from_bytes(
            normalized,
            response.content,
            response.headers.get("content-type", ""),
        )
        if len(content) < 10:
            return None
        return {
            "name": normalized,
            "content": content[:20000],
            "source_type": "link",
            "url": normalized,
        }


async def _resolve_lookup_names(queries: List[str], db: AsyncSession) -> List[dict]:
    resolved: List[dict] = []
    seen = set()

    for query in queries[:MAX_LOOKUP_NAMES]:
        name = (query or "").strip()
        if not name:
            continue

        statement = (
            select(PolicyDocument)
            .where(or_(PolicyDocument.title.contains(name), PolicyDocument.content.contains(name)))
            .order_by(PolicyDocument.id.desc())
            .limit(3)
        )
        local_result = await db.execute(statement)
        local_docs = local_result.scalars().all()

        for doc in local_docs:
            dedupe_key = f"db-{doc.id}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            resolved.append(
                {
                    "name": doc.title,
                    "content": (doc.content or "")[:20000],
                    "source_type": "lookup",
                }
            )

        if local_docs:
            continue

        remote_docs = await orchestrator.policy_agent.search_relevant_policies(name)
        for index, doc in enumerate(remote_docs[:2]):
            dedupe_key = f"vector-{name}-{index}-{doc.get('title', '')}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            resolved.append(
                {
                    "name": doc.get("title") or name,
                    "content": (doc.get("content") or "")[:20000],
                    "source_type": "lookup",
                }
            )

    return resolved


@router.post("/parse-uploaded-files")
async def parse_uploaded_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传 1 个文件")
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"单次最多上传 {MAX_UPLOAD_FILES} 个文件")

    parsed_files = []
    for upload in files:
        parsed_files.append(await _parse_upload_file(upload))

    return {
        "success": True,
        "count": len(parsed_files),
        "files": parsed_files,
    }


@router.get("/llm-health")
async def get_llm_health():
    """检查当前 LLM 配置与连通性。"""
    health = await check_llm_health()
    return {
        "success": bool(health.get("reachable")),
        "health": health,
        "runtime": get_llm_runtime_config(),
    }


@router.post("/start-mining")
async def start_mining(request: MiningRequest, db: AsyncSession = Depends(get_db)):
    """启动多智能体指标挖掘。"""
    merged_standard_texts = list(request.standard_texts)
    normalized_links = [item.strip() for item in request.web_links if item and item.strip()]
    lookup_names = [item.strip() for item in request.lookup_names if item and item.strip()][:MAX_LOOKUP_NAMES]
    uploaded_documents = [
        item for item in request.uploaded_documents
        if item and isinstance(item.content, str) and item.content.strip()
    ][:MAX_UPLOAD_FILES]

    fetched_link_documents = []
    for url in normalized_links:
        try:
            parsed_doc = await _fetch_url_document(url)
            if parsed_doc:
                fetched_link_documents.append(parsed_doc)
                merged_standard_texts.append(parsed_doc["content"])
            else:
                merged_standard_texts.append(f"链接内容过短或无法解析：{url}")
        except Exception:
            merged_standard_texts.append(f"链接抓取失败：{url}")

    resolved_lookup_documents = await _resolve_lookup_names(lookup_names, db)
    merged_standard_texts.extend(
        [item["content"] for item in resolved_lookup_documents if item.get("content")]
    )
    merged_standard_texts.extend([item.content.strip() for item in uploaded_documents])

    mining_demand = (request.mining_demand or "level3").strip().lower() or "level3"
    if mining_demand not in MINING_DEMAND_LABELS:
        raise HTTPException(status_code=400, detail="mining_demand must be one of: level1, level2, level3")

    try:
        result = await orchestrator.run_pipeline(
            policy_texts=request.policy_texts,
            standard_texts=merged_standard_texts,
            case_texts=request.case_texts,
            web_links=normalized_links,
            mining_demand=mining_demand,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    indicators = result.get("indicators", [])
    new_indicators = result.get("new_indicators", [])
    existing_indicators = await review_module.get_all_indicators(db)
    existing_keys = {
        _build_indicator_dedupe_key(item)
        for item in existing_indicators
        if isinstance(item, dict)
    }

    imported_indicators = []
    imported_key_set = set()
    for item in new_indicators:
        if not isinstance(item, dict):
            continue
        dedupe_key = _build_indicator_dedupe_key(item)
        if dedupe_key in existing_keys or dedupe_key in imported_key_set:
            continue
        imported_key_set.add(dedupe_key)
        imported_indicators.append(item)

    imported_count = await review_module.batch_import(db, imported_indicators)
    demand_label = MINING_DEMAND_LABELS[mining_demand]

    return {
        "success": True,
        "task_id": result["task_id"],
        "candidate_level": mining_demand,
        "stats": result["stats"],
        "indicators": result.get("display_indicators", new_indicators),
        "all_indicators": indicators,
        "new_indicators": new_indicators,
        "imported_count": imported_count,
        "imported_indicators": imported_indicators,
        "policy_data": result.get("policy_data", {}),
        "dimension_data": result["dimension_data"],
        "agent_outputs": result.get("agent_outputs", {}),
        "request_context": result.get("request_context", {}),
        "uploaded_documents": [item.model_dump() for item in uploaded_documents],
        "resolved_link_documents": fetched_link_documents,
        "resolved_lookup_documents": resolved_lookup_documents,
        "name_review_required": True,
        "workflow_guardrails": {
            "must_human_review": [
                "指标名称与指标采纳",
                f"新增{demand_label}入库前确认",
            ],
            "llm_only_for": [
                f"围绕文档生成候选{demand_label}",
                "读取政策与标准信息提取线索",
            ],
        },
        "pending_review_count": imported_count,
        "message": (
            f"成功挖掘 {result.get('stats', {}).get('selected_indicators_count', len(new_indicators))} 个"
            f"{demand_label}，导入 {imported_count} 个新指标。"
            f"当前导入项均为待审校，需人工确认后方可采纳。"
        ),
    }


@router.get("/logs")
async def get_agent_logs():
    """获取智能体运行日志。"""
    return {"logs": orchestrator.get_logs()}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时推送智能体运行日志。"""
    await websocket.accept()

    async def send_update(log_entry: dict):
        try:
            await websocket.send_text(json.dumps(log_entry, ensure_ascii=False))
        except Exception:
            pass

    orchestrator.add_websocket_callback(send_update)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        orchestrator.remove_websocket_callback(send_update)
