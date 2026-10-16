"""Pure normalize + hash helpers for Bronze price rows."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from bronze.schema import BUSINESS_COLUMNS

_TICKER_RE = re.compile(r"^[A-Z]{1,10}$")


class NormalizeError(ValueError):
    """Raised when a raw row cannot be normalized; .reason is human-readable."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _as_float(name: str, value: Any) -> float:
    if value is None or value == "":
        raise NormalizeError(f"{name} is missing")
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise NormalizeError(f"{name} is not numeric: {value!r}") from exc
    if n != n:  # NaN
        raise NormalizeError(f"{name} is NaN")
    if n <= 0:
        raise NormalizeError(f"{name} must be > 0, got {n}")
    return n


def _as_int_volume(value: Any) -> int:
    if value is None or value == "":
        raise NormalizeError("volume is missing")
    try:
        # allow "1000" or 1000.0
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise NormalizeError(f"volume is not numeric: {value!r}") from exc
    if n != int(n) or n < 0:
        raise NormalizeError(f"volume must be a non-negative integer, got {value!r}")
    return int(n)


def _parse_trade_date(value: Any) -> str:
    if value is None or value == "":
        raise NormalizeError("trade_date is missing")
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    # Accept YYYY-MM-DD only for stability
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError as exc:
        raise NormalizeError(f"trade_date must be YYYY-MM-DD, got {value!r}") from exc


def source_row_hash(business: dict[str, Any]) -> str:
    """Stable SHA-256 hex of business columns in fixed order (pipe-joined)."""
    parts = []
    for col in BUSINESS_COLUMNS:
        v = business[col]
        if col == "volume":
            parts.append(str(int(v)))
        elif col in ("open", "high", "low", "close"):
            parts.append(f"{float(v):.6f}")
        else:
            parts.append(str(v))
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize one raw extract dict into business columns.

    - ticker → uppercase letters
    - trade_date → ISO date string
    - OHLC → float > 0; low ≤ open/close ≤ high
    - volume → non-negative int

    Raises NormalizeError with a clear .reason on bad input.
    """
    if not isinstance(raw, dict):
        raise NormalizeError("row must be a dict")

    ticker_raw = raw.get("ticker")
    if ticker_raw is None or str(ticker_raw).strip() == "":
        raise NormalizeError("ticker is missing")
    ticker = str(ticker_raw).strip().upper()
    if not _TICKER_RE.match(ticker):
        raise NormalizeError(f"ticker must be 1–10 letters, got {ticker_raw!r}")

    trade_date = _parse_trade_date(raw.get("trade_date"))
    o = _as_float("open", raw.get("open"))
    h = _as_float("high", raw.get("high"))
    low = _as_float("low", raw.get("low"))
    c = _as_float("close", raw.get("close"))
    vol = _as_int_volume(raw.get("volume"))

    if low > h:
        raise NormalizeError(f"low ({low}) > high ({h})")
    if not (low <= o <= h):
        raise NormalizeError(f"open ({o}) not between low ({low}) and high ({h})")
    if not (low <= c <= h):
        raise NormalizeError(f"close ({c}) not between low ({low}) and high ({h})")

    return {
        "ticker": ticker,
        "trade_date": trade_date,
        "open": o,
        "high": h,
        "low": low,
        "close": c,
        "volume": vol,
    }
