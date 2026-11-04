"""Policy document service."""

import hashlib
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import PolicyDocument
from utils.vector_store import vector_store

RELEVANCE_KEYWORDS = [
    "文化",
    "传统",
    "礼仪",
    "价值观",
    "公平",
    "隐私",
    "伦理",
    "场景",
    "任务",
    "语义",
    "模型",
    "数据质量",
    "科学",
    "指标体系",
]


class PolicyDocumentService:
    """Unified service for policy document storage and tagging."""

    @staticmethod
    def build_content_hash(content: str) -> str:
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def relevance_score(text: str) -> float:
        if not text:
            return 0.0
        hit = sum(1 for k in RELEVANCE_KEYWORDS if k in text)
        return min(1.0, hit / 8.0)

    @staticmethod
    def infer_dimension_tags(text: str) -> List[str]:
        tags: List[str] = []

        if any(k in text for k in ["文化", "传统", "礼仪", "价值观", "公平", "隐私", "伦理", "民族"]):
            tags.append("文化适配层")
        if any(k in text for k in ["场景", "应用", "任务", "语义", "模型", "数据质量", "性能", "科学"]):
            tags.append("场景支撑层")

        return tags or ["文化适配层", "场景支撑层"]

    @staticmethod
    def is_suspected_garbled(text: Optional[str]) -> bool:
        """Detect likely mojibake/garbled text with conservative rules."""
        if not text:
            return True
        if "锟" in text:
            return True

        q_count = text.count("?")
        if q_count >= 8 and q_count / max(1, len(text)) >= 0.08:
            return True
        if "???" in text:
            return True

        if re.search(r"[?]{6,}|[锟]{2,}", text):
            return True

        return False

    @classmethod
    async def build_quality_report(cls, db: AsyncSession, sample_limit: int = 20) -> Dict:
        result = await db.execute(select(PolicyDocument).order_by(PolicyDocument.id.desc()))
        docs = result.scalars().all()

        total = len(docs)
        suspected = []
        too_short = []
        by_type = {}

        for doc in docs:
            by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1

            content = (doc.content or "").strip()
            title = (doc.title or "").strip()

            if len(content) < 20:
                too_short.append(doc.id)

            if cls.is_suspected_garbled(title) or cls.is_suspected_garbled(content):
                suspected.append(
                    {
                        "id": doc.id,
                        "doc_type": doc.doc_type,
                        "title": title[:120],
                        "source_site": doc.source_site,
                        "source_url": doc.source_url,
                    }
                )

        return {
            "total": total,
            "by_doc_type": by_type,
            "suspected_garbled_count": len(suspected),
            "too_short_count": len(too_short),
            "suspected_garbled_samples": suspected[:sample_limit],
            "too_short_ids": too_short[:sample_limit],
        }

    @classmethod
    async def clean_documents(
        cls,
        db: AsyncSession,
        *,
        dry_run: bool = True,
        include_too_short: bool = False,
        short_threshold: int = 20,
        only_source_site: Optional[str] = "manual_input",
        allowed_doc_types: Optional[List[str]] = None,
    ) -> Dict:
        report = await cls.build_quality_report(db)

        result = await db.execute(select(PolicyDocument))
        docs = result.scalars().all()

        to_delete_ids = []
        for doc in docs:
            if only_source_site and doc.source_site != only_source_site:
                continue
            if allowed_doc_types and doc.doc_type not in allowed_doc_types:
                continue

            content = (doc.content or "").strip()
            title = (doc.title or "").strip()
            garbled = cls.is_suspected_garbled(title) or cls.is_suspected_garbled(content)
            short = len(content) < short_threshold
            if garbled or (include_too_short and short):
                to_delete_ids.append(doc.id)

        if dry_run:
            return {
                "dry_run": True,
                "report": report,
                "filters": {
                    "only_source_site": only_source_site,
                    "allowed_doc_types": allowed_doc_types,
                    "include_too_short": include_too_short,
                    "short_threshold": short_threshold,
                },
                "to_delete_count": len(to_delete_ids),
                "to_delete_ids": to_delete_ids[:100],
            }

        if to_delete_ids:
            await db.execute(delete(PolicyDocument).where(PolicyDocument.id.in_(to_delete_ids)))
            await db.commit()

        return {
            "dry_run": False,
            "filters": {
                "only_source_site": only_source_site,
                "allowed_doc_types": allowed_doc_types,
                "include_too_short": include_too_short,
                "short_threshold": short_threshold,
            },
            "deleted_count": len(to_delete_ids),
            "deleted_ids": to_delete_ids[:100],
            "report_before": report,
            "report_after": await cls.build_quality_report(db),
        }

    @classmethod
    async def save_document(
        cls,
        db: AsyncSession,
        *,
        title: str,
        content: str,
        doc_type: str,
        source_site: str = "manual_input",
        source_url: Optional[str] = None,
        publisher: Optional[str] = None,
        published_at: Optional[datetime] = None,
        crawl_batch_id: Optional[str] = None,
        min_relevance: float = 0.35,
    ) -> Dict:
        normalized_content = content.strip()
        if len(normalized_content) < 10:
            return {"saved": False, "duplicated": False, "reason": "content_too_short"}

        content_hash = cls.build_content_hash(normalized_content)

        existing = await db.execute(
            select(PolicyDocument).where(PolicyDocument.content_hash == content_hash)
        )
        if existing.scalar_one_or_none():
            return {"saved": False, "duplicated": True, "reason": "duplicate"}

        score = cls.relevance_score(normalized_content)
        if score < min_relevance:
            return {"saved": False, "duplicated": False, "reason": "low_relevance", "score": score}

        tags = cls.infer_dimension_tags(normalized_content)

        doc = PolicyDocument(
            title=title.strip()[:200],
            content=normalized_content,
            doc_type=doc_type,
            source_site=source_site,
            source_url=source_url,
            publisher=publisher,
            published_at=published_at,
            fetched_at=datetime.utcnow(),
            relevance_score=score,
            dimension_tags=json.dumps(tags, ensure_ascii=False),
            content_hash=content_hash,
            crawl_batch_id=crawl_batch_id,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        vector_store.add_policy(
            doc_id=f"policy_db_{doc.id}",
            content=normalized_content,
            metadata={
                "title": doc.title,
                "doc_type": doc.doc_type,
                "source_url": source_url or "",
                "source_site": source_site,
            },
        )

        return {
            "saved": True,
            "duplicated": False,
            "id": doc.id,
            "score": score,
            "dimension_tags": tags,
        }


policy_document_service = PolicyDocumentService()
