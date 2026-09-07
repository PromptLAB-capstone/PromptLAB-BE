from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.models import FundingProgram
from app.db.session import AsyncSessionLocal


DEFAULT_CSV = ROOT / "data" / "postgres" / "funding_programs.csv"


def clean_text(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip()


def null_if_blank(value: Any) -> str | None:
    text = clean_text(value)
    return text or None


def parse_date(value: Any) -> date | None:
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_int(value: Any) -> int | None:
    text = clean_text(value).replace(",", "")
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def parse_keywords(value: Any) -> list[str] | None:
    text = clean_text(value)
    if not text:
        return None
    return [item.strip() for item in text.replace("#", ",").split(",") if item.strip()]


def parse_json(value: Any) -> dict | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"note": text}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    output: list[dict[str, Any]] = []
    for row in rows:
        program_id = clean_text(row.get("program_id"))
        title = clean_text(row.get("title"))
        if not program_id or not title:
            continue
        output.append(
            {
                "program_id": program_id,
                "title": title,
                "region": null_if_blank(row.get("region")),
                "stage": null_if_blank(row.get("stage")),
                "eligibility_json": parse_json(row.get("eligibility_json")),
                "open_date": parse_date(row.get("open_date")),
                "deadline": parse_date(row.get("deadline")),
                "max_amount": parse_int(row.get("max_amount")),
                "support_amount_text": null_if_blank(row.get("support_amount_text")),
                "source": null_if_blank(row.get("source")),
                "source_url": null_if_blank(row.get("source_url")),
                "description": null_if_blank(row.get("description")),
                "keywords": parse_keywords(row.get("keywords")),
            }
        )
    return output


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import funding_programs CSV into Postgres.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help="CSV path. Defaults to data/postgres/funding_programs.csv",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print row count without DB writes.")
    args = parser.parse_args()

    rows = load_rows(args.csv)
    if args.dry_run:
        print(f"funding_programs: {len(rows)}")
        return
    if not rows:
        print("funding_programs: 0")
        return

    stmt = insert(FundingProgram).values(rows)
    update_columns = {
        column.name: getattr(stmt.excluded, column.name)
        for column in FundingProgram.__table__.columns
        if column.name not in {"program_id", "created_at"}
    }

    async with AsyncSessionLocal() as session:
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[FundingProgram.program_id],
                set_=update_columns,
            )
        )
        await session.commit()

    print(f"Imported funding_programs: {len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
