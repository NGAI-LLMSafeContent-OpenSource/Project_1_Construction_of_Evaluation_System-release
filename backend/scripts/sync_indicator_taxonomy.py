"""Sync the new two-layer indicator taxonomy into the SQLite database.

This is a one-off maintenance script. It upserts the 12 level-2 indicator
descriptions from backend/ontology/new_indicator_taxonomy.py without deleting
or resetting any existing database rows.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from models.schemas import AsyncSessionLocal, Indicator, init_db  # noqa: E402
from ontology.new_indicator_taxonomy import NEW_INDICATOR_ONTOLOGY  # noqa: E402


SYNC_FIELDS = (
    "definition",
    "positive_example",
    "negative_example",
    "scoring_rule",
    "skill_name",
    "formula_type",
    "source",
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _is_level2_description(indicator: Indicator, item: dict) -> bool:
    level3 = _clean(indicator.level3)
    level2 = _clean(item.get("level2"))
    return level3 in {"", level2}


async def _find_existing(session, item: dict) -> Indicator | None:
    exact_name = _clean(item.get("level2"))
    result = await session.execute(
        select(Indicator)
        .where(Indicator.dimension == item.get("dimension"))
        .where(Indicator.level1 == item.get("level1"))
        .where(Indicator.level2 == item.get("level2"))
        .order_by(Indicator.id)
    )

    candidates = [row for row in result.scalars().all() if _is_level2_description(row, item)]
    if not candidates:
        if exact_name != "科学真实性":
            return None

        result = await session.execute(
            select(Indicator)
            .where(Indicator.level2 == item.get("level2"))
            .order_by(Indicator.id)
        )
        candidates = [row for row in result.scalars().all() if _is_level2_description(row, item)]
        if not candidates:
            return None

    approved = [row for row in candidates if _clean(row.name) == exact_name and row.status == "approved"]
    if approved:
        return approved[0]

    same_name = [row for row in candidates if _clean(row.name) == exact_name]
    return same_name[0] if same_name else candidates[0]


def _apply_item(indicator: Indicator, item: dict) -> bool:
    changed = False
    field_values = {
        "name": item.get("level2"),
        "dimension": item.get("dimension"),
        "level1": item.get("level1"),
        "level2": item.get("level2"),
        "level3": "",
        "status": "approved",
        **{field: item.get(field) for field in SYNC_FIELDS},
    }

    for field, value in field_values.items():
        if getattr(indicator, field, None) != value:
            setattr(indicator, field, value)
            changed = True

    if changed:
        indicator.updated_at = datetime.utcnow()

    return changed


async def sync_taxonomy() -> dict:
    await init_db()

    inserted = 0
    updated = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        for item in NEW_INDICATOR_ONTOLOGY:
            existing = await _find_existing(session, item)
            if existing:
                if _apply_item(existing, item):
                    updated += 1
                else:
                    skipped += 1
                continue

            indicator = Indicator(
                name=item.get("level2"),
                dimension=item.get("dimension"),
                level1=item.get("level1"),
                level2=item.get("level2"),
                level3="",
                status="approved",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **{field: item.get(field) for field in SYNC_FIELDS},
            )
            session.add(indicator)
            inserted += 1

        await session.commit()

        synced = 0
        for item in NEW_INDICATOR_ONTOLOGY:
            existing = await _find_existing(session, item)
            if existing and all(getattr(existing, field, None) == item.get(field) for field in SYNC_FIELDS):
                synced += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "expected": len(NEW_INDICATOR_ONTOLOGY),
        "synced": synced,
        "all_synced": synced == len(NEW_INDICATOR_ONTOLOGY),
    }


def main() -> None:
    result = asyncio.run(sync_taxonomy())
    print(f"inserted: {result['inserted']}")
    print(f"updated: {result['updated']}")
    print(f"skipped: {result['skipped']}")
    print(f"synced: {result['synced']}/{result['expected']}")
    print(f"all_synced: {result['all_synced']}")


if __name__ == "__main__":
    main()
