"""Canonical Bronze schema for market.prices ingest."""

from __future__ import annotations

# Business columns (mirror Day 1 Postgres market.prices)
BUSINESS_COLUMNS: tuple[str, ...] = (
    "ticker",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

# Ingest metadata appended at Bronze land time
META_COLUMNS: tuple[str, ...] = (
    "_ingested_at",  # UTC ISO-8601 timestamp
    "_source_system",  # e.g. postgres.market.prices
    "_batch_id",  # uuid / run id
    "_source_row_hash",  # stable hash of business keys + values
)

BRONZE_COLUMNS: tuple[str, ...] = BUSINESS_COLUMNS + META_COLUMNS

SOURCE_SYSTEM_DEFAULT = "postgres.market.prices"

# Types (documentation + local validation helpers)
COLUMN_TYPES: dict[str, str] = {
    "ticker": "STRING",
    "trade_date": "DATE",
    "open": "DOUBLE",
    "high": "DOUBLE",
    "low": "DOUBLE",
    "close": "DOUBLE",
    "volume": "BIGINT",
    "_ingested_at": "TIMESTAMP",
    "_source_system": "STRING",
    "_batch_id": "STRING",
    "_source_row_hash": "STRING",
}
