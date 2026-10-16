"""Land a batch of raw price rows into Bronze-shaped dicts (+ optional JSONL)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bronze.normalize import NormalizeError, normalize_row, source_row_hash
from bronze.schema import SOURCE_SYSTEM_DEFAULT


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def land_batch(
    raw_rows: list[dict[str, Any]],
    batch_id: str,
    source_system: str = SOURCE_SYSTEM_DEFAULT,
    *,
    ingested_at: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """
    Normalize raw rows and attach Bronze metadata.

    Returns (landed_rows, rejected) where rejected items are
    {"reason": str, "raw": json-ish summary}.
    """
    if not batch_id or not str(batch_id).strip():
        raise ValueError("batch_id is required")
    ts = ingested_at or _utc_now_iso()
    landed: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []

    for raw in raw_rows:
        try:
            biz = normalize_row(raw)
        except NormalizeError as exc:
            rejected.append({"reason": exc.reason, "raw": str(raw)})
            continue
        row = {
            **biz,
            "_ingested_at": ts,
            "_source_system": source_system,
            "_batch_id": str(batch_id),
            "_source_row_hash": source_row_hash(biz),
        }
        landed.append(row)
    return landed, rejected


def write_jsonl(rows: list[dict[str, Any]], path: Path | str) -> int:
    """Append Bronze rows as JSON Lines. Returns lines written."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=False) + "\n")
    return len(rows)
