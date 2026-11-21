"""Safely mark obsolete indicators ignored and upsert the fixed taxonomy nodes.

This script does not delete the database file and does not reset the database.
It only updates rows in the indicators table.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from ontology.new_indicator_taxonomy import (  # noqa: E402
    ALLOWED_DIMENSIONS,
    LEVEL1_TO_DIMENSION,
    LEVEL2_TO_LEVEL1,
    NEW_INDICATOR_ONTOLOGY,
)


OLD_KEYWORDS = {
    "价值核心维度",
    "公民层面",
    "国家层面",
    "社会层面",
    "富强",
    "民主",
    "文明",
    "和谐",
    "自由",
    "平等",
    "公正",
    "法治",
    "爱国",
    "敬业",
    "诚信",
    "友善",
}


def resolve_sqlite_path(database_url: str) -> Path:
    prefix = "sqlite+aiosqlite:///"
    if database_url.startswith(prefix):
        raw_path = database_url[len(prefix) :]
    elif database_url.startswith("sqlite:///"):
        raw_path = database_url[len("sqlite:///") :]
    else:
        raise SystemExit(f"Only SQLite DATABASE_URL is supported by this script: {database_url}")

    path = Path(raw_path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path.resolve()


def row_is_current(row: sqlite3.Row) -> bool:
    level2 = (row["level2"] or "").strip()
    level1 = (row["level1"] or "").strip()
    dimension = (row["dimension"] or "").strip()
    level3 = (row["level3"] or "").strip()

    if level2 not in LEVEL2_TO_LEVEL1:
        return False
    expected_level1 = LEVEL2_TO_LEVEL1[level2]
    expected_dimension = LEVEL1_TO_DIMENSION[expected_level1]
    if level1 != expected_level1 or dimension != expected_dimension:
        return False

    text = " ".join(str(row[key] or "") for key in ("name", "level1", "level2", "level3", "definition"))
    if any(keyword in text for keyword in OLD_KEYWORDS):
        return False

    return True if level3 else True


def upsert_level2(conn: sqlite3.Connection, item: dict) -> None:
    now = datetime.utcnow().isoformat(sep=" ")
    existing = conn.execute(
        """
        SELECT id FROM indicators
        WHERE level1 = ? AND level2 = ? AND COALESCE(level3, '') = ''
        ORDER BY id ASC
        LIMIT 1
        """,
        (item["level1"], item["level2"]),
    ).fetchone()

    payload = {
        "name": item["level2"],
        "level1": item["level1"],
        "level2": item["level2"],
        "level3": "",
        "level4": None,
        "definition": item["definition"],
        "formula": "",
        "source": item.get("source", ""),
        "status": "approved",
        "updated_at": now,
        "review_comment": "",
        "dimension": item["dimension"],
        "formula_type": "",
        "explain_reason": "",
        "positive_example": item.get("positive_example", ""),
        "negative_example": item.get("negative_example", ""),
        "scoring_rule": item.get("scoring_rule", ""),
        "skill_name": "",
        "demo_flow": "",
    }

    if existing:
        payload["id"] = existing["id"]
        conn.execute(
            """
            UPDATE indicators
            SET name=:name, level1=:level1, level2=:level2, level3=:level3, level4=:level4,
                definition=:definition, formula=:formula, source=:source, status=:status,
                updated_at=:updated_at, review_comment=:review_comment, dimension=:dimension,
                formula_type=:formula_type, explain_reason=:explain_reason,
                positive_example=:positive_example, negative_example=:negative_example,
                scoring_rule=:scoring_rule, skill_name=:skill_name, demo_flow=:demo_flow
            WHERE id=:id
            """,
            payload,
        )
    else:
        payload["created_at"] = now
        conn.execute(
            """
            INSERT INTO indicators (
                name, level1, level2, level3, level4, definition, formula, source, status,
                created_at, updated_at, review_comment, dimension, formula_type, explain_reason,
                positive_example, negative_example, scoring_rule, skill_name, demo_flow
            )
            VALUES (
                :name, :level1, :level2, :level3, :level4, :definition, :formula, :source, :status,
                :created_at, :updated_at, :review_comment, :dimension, :formula_type, :explain_reason,
                :positive_example, :negative_example, :scoring_rule, :skill_name, :demo_flow
            )
            """,
            payload,
        )


def main() -> None:
    load_dotenv(BACKEND_DIR / ".env")
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chroma_db/value_eval_main.db")
    db_path = resolve_sqlite_path(database_url)

    print(f"DATABASE_URL: {database_url}")
    print(f"SQLite file: {db_path}")

    if not db_path.exists():
        raise SystemExit(f"Database file does not exist: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM indicators").fetchall()
        obsolete_ids = [row["id"] for row in rows if not row_is_current(row)]

        if obsolete_ids:
            placeholders = ",".join("?" for _ in obsolete_ids)
            conn.execute(
                f"UPDATE indicators SET status = 'ignored', updated_at = ? WHERE id IN ({placeholders})",
                [datetime.utcnow().isoformat(sep=" "), *obsolete_ids],
            )

        for item in NEW_INDICATOR_ONTOLOGY:
            upsert_level2(conn, item)

        conn.commit()

        print(f"清理旧指标数量: {len(obsolete_ids)}")
        print(f"更新二级指标数量: {len(NEW_INDICATOR_ONTOLOGY)}")
        print("当前保留的一级、二级指标列表:")
        for dimension, layer_name in ALLOWED_DIMENSIONS.items():
            print(f"- {layer_name} ({dimension})")
            for level1, dim in LEVEL1_TO_DIMENSION.items():
                if dim != dimension:
                    continue
                print(f"  - {level1}")
                for level2, parent in LEVEL2_TO_LEVEL1.items():
                    if parent == level1:
                        print(f"    - {level2}")

        print("被标记 ignored 的旧指标示例:")
        for row in rows:
            if row["id"] in obsolete_ids[:20]:
                print(f"- id={row['id']} name={row['name']} path={row['level1']} / {row['level2']} / {row['level3']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

