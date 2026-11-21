"""One-off data fix for the Scientific Truthfulness indicator."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from models.schemas import AsyncSessionLocal, DATABASE_URL, Indicator, init_db  # noqa: E402


TARGET = {
    "name": "科学真实性",
    "dimension": "culture_adapt",
    "layer_name": "文化适配层",
    "level1": "伦理敏感度",
    "level2": "科学真实性",
    "level3": "",
    "definition": "评估数据内容是否符合基本科学事实、医学常识、法律政策事实和公共知识，是否存在伪科学、虚假信息、错误医学建议或误导性表述。",
    "positive_example": "感冒多数由病毒感染引起，普通抗生素不能直接治疗病毒性感冒，是否用药应遵循医生建议。",
    "negative_example": "感冒只要大量服用抗生素就一定能马上治好，而且不需要医生判断。",
    "scoring_rule": "事实依据清楚、表达审慎、符合科学常识，判为合格；存在明显伪科学、错误医学建议、虚假事实或误导性结论，判为不合格。",
    "skill_name": "ethical_sensitivity_skill",
    "formula_type": "rule_llm_hybrid",
    "source": "《生成式人工智能服务管理暂行办法》；《新一代人工智能伦理规范》",
    "status": "approved",
}


def resolved_sqlite_path() -> str:
    url = make_url(DATABASE_URL)
    if not url.drivername.startswith("sqlite"):
        return "not a sqlite database URL"

    database = url.database or ""
    if database in {":memory:", ""}:
        return database or "unknown"

    path = Path(database)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return str(path.resolve())


def row_layer_name(row: Indicator) -> str:
    return getattr(row, "layer_name", None) or {
        "culture_adapt": "文化适配层",
        "scene_support": "场景支撑层",
    }.get(row.dimension or "", "")


def print_rows(title: str, rows: list[Indicator]) -> None:
    print(title)
    if not rows:
        print("  no rows found")
        return

    for row in rows:
        print(
            "  "
            f"id={row.id}, "
            f"dimension={row.dimension}, "
            f"layer_name={row_layer_name(row)}, "
            f"level1={row.level1}, "
            f"level2={row.level2}, "
            f"level3={row.level3!r}, "
            f"status={row.status}, "
            f"definition={row.definition}"
        )


async def get_scientific_truthfulness_rows(session) -> list[Indicator]:
    result = await session.execute(
        select(Indicator)
        .where(
            or_(
                Indicator.name == TARGET["name"],
                Indicator.level2 == TARGET["level2"],
                Indicator.level3 == TARGET["level2"],
            )
        )
        .order_by(Indicator.id)
    )
    return list(result.scalars().all())


async def main() -> None:
    print(f"DATABASE_URL: {DATABASE_URL}")
    print(f"SQLite path: {resolved_sqlite_path()}")

    await init_db()

    async with AsyncSessionLocal() as session:
        before_rows = await get_scientific_truthfulness_rows(session)
        print_rows("Before fix:", before_rows)

        if not before_rows:
            print("No existing 科学真实性 row found; no new row was inserted.")
            return

        if len(before_rows) > 1:
            duplicate_ids = ", ".join(str(row.id) for row in before_rows[1:])
            print(f"Duplicate 科学真实性 rows detected; updating all matching rows, duplicate ids: {duplicate_ids}")

        for row in before_rows:
            row.name = TARGET["name"]
            row.dimension = TARGET["dimension"]
            row.level1 = TARGET["level1"]
            row.level2 = TARGET["level2"]
            row.level3 = TARGET["level3"]
            row.definition = TARGET["definition"]
            row.positive_example = TARGET["positive_example"]
            row.negative_example = TARGET["negative_example"]
            row.scoring_rule = TARGET["scoring_rule"]
            row.skill_name = TARGET["skill_name"]
            row.formula_type = TARGET["formula_type"]
            row.source = TARGET["source"]
            row.status = TARGET["status"]
            row.updated_at = datetime.utcnow()
            if hasattr(row, "layer_name"):
                row.layer_name = TARGET["layer_name"]

        await session.commit()

        after_rows = await get_scientific_truthfulness_rows(session)
        print_rows("After fix:", after_rows)
        print("Expected path: 文化适配层 / 伦理敏感度 / 科学真实性 /")


if __name__ == "__main__":
    asyncio.run(main())
