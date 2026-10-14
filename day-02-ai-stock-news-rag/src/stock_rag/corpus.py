"""Load the bundled sample stock-news corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "news_sample.json"


def load_corpus(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load news JSON; each item has id, date, ticker, headline, text."""
    data_path = Path(path) if path else DEFAULT_DATA
    if not data_path.is_file():
        raise FileNotFoundError(f"Corpus not found: {data_path}")
    with data_path.open(encoding="utf-8") as f:
        docs = json.load(f)
    if not isinstance(docs, list) or not docs:
        raise ValueError("Corpus must be a non-empty JSON list")
    for i, doc in enumerate(docs):
        for key in ("id", "date", "ticker", "headline", "text"):
            if key not in doc or not str(doc[key]).strip():
                raise ValueError(f"Doc[{i}] missing required field: {key}")
    return docs


def doc_text(doc: dict[str, Any]) -> str:
    """Flatten a news doc into one searchable string."""
    return f"{doc['ticker']} {doc['headline']} {doc['text']}"
