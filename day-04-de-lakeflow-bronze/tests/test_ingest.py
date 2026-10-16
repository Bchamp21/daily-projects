"""Tests for bronze.ingest.land_batch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bronze.ingest import land_batch, write_jsonl
from bronze.schema import BRONZE_COLUMNS, META_COLUMNS


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_extract.json"


def test_land_sample_extract_count():
    raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
    landed, rejected = land_batch(raw, batch_id="batch-test-1")
    # 12 rows in sample; 2 dirty (BADX low>high, ZZ bad date) → 10 landed
    assert len(raw) == 12
    assert len(landed) == 10
    assert len(rejected) == 2
    assert all("reason" in r for r in rejected)


def test_metadata_fields_present():
    landed, _ = land_batch(
        [
            {
                "ticker": "aapl",
                "trade_date": "2026-10-01",
                "open": 1,
                "high": 2,
                "low": 0.5,
                "close": 1.5,
                "volume": 10,
            }
        ],
        batch_id="b1",
        source_system="postgres.market.prices",
        ingested_at="2026-10-15T18:00:00Z",
    )
    assert len(landed) == 1
    row = landed[0]
    for col in BRONZE_COLUMNS:
        assert col in row
    assert row["_batch_id"] == "b1"
    assert row["_source_system"] == "postgres.market.prices"
    assert row["_ingested_at"] == "2026-10-15T18:00:00Z"
    assert len(row["_source_row_hash"]) == 64
    assert row["ticker"] == "AAPL"


def test_empty_batch_id_raises():
    with pytest.raises(ValueError):
        land_batch([], batch_id="")


def test_write_jsonl(tmp_path: Path):
    landed, _ = land_batch(
        [
            {
                "ticker": "MSFT",
                "trade_date": "2026-10-01",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "volume": 100,
            }
        ],
        batch_id="j1",
        ingested_at="2026-10-15T18:00:00Z",
    )
    out = tmp_path / "prices.jsonl"
    n = write_jsonl(landed, out)
    assert n == 1
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["ticker"] == "MSFT"
    for m in META_COLUMNS:
        assert m in parsed
