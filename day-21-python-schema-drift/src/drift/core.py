"""Schema drift detector: compare a CSV's inferred schema to a data contract."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

# Type ladder: a column's type is the "widest" type that fits every value.
ORDER = ["int", "float", "date", "timestamp", "string"]
# Widening that downstream readers can handle without breaking.
SAFE_WIDENING = {("int", "float"), ("date", "timestamp")}


def infer_value(v: str) -> str | None:
    """Return the narrowest type for one cell, or None for empty."""
    if v.strip() == "":
        return None
    try:
        int(v)
        return "int"
    except ValueError:
        pass
    try:
        float(v)
        return "float"
    except ValueError:
        pass
    try:
        date.fromisoformat(v)
        return "date"
    except ValueError:
        pass
    try:
        datetime.fromisoformat(v)
        return "timestamp"
    except ValueError:
        return "string"


def merge(a: str | None, b: str | None) -> str | None:
    """Combine two types into one that fits both."""
    if a is None or a == b:
        return b if a is None else a
    if b is None:
        return a
    if {a, b} == {"int", "float"}:
        return "float"
    if {a, b} == {"date", "timestamp"}:
        return "timestamp"
    return "string"


@dataclass
class Column:
    type: str
    nullable: bool


def infer_schema(path: Path, sample_rows: int = 10_000) -> dict[str, Column]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        types: dict[str, str | None] = {c: None for c in reader.fieldnames or []}
        nulls = {c: False for c in types}
        for i, row in enumerate(reader):
            if i >= sample_rows:
                break
            for col, val in row.items():
                t = infer_value(val or "")
                if t is None:
                    nulls[col] = True
                types[col] = merge(types[col], t)
    return {c: Column(t or "string", nulls[c]) for c, t in types.items()}


def load_contract(path: Path) -> dict[str, Column]:
    raw = json.loads(Path(path).read_text())
    return {c: Column(spec["type"], spec.get("nullable", True)) for c, spec in raw["columns"].items()}


class Severity(str, Enum):
    OK = "ok"
    WARN = "warn"       # safe: new column, safe widening
    BREAK = "break"     # unsafe: removed column, narrowing, new nulls


@dataclass
class Change:
    column: str
    kind: str
    detail: str
    severity: Severity


def diff(contract: dict[str, Column], actual: dict[str, Column]) -> list[Change]:
    out: list[Change] = []
    for col in contract.keys() - actual.keys():
        out.append(Change(col, "removed", "column missing", Severity.BREAK))
    for col in actual.keys() - contract.keys():
        out.append(Change(col, "added", f"new {actual[col].type} column", Severity.WARN))
    for col in contract.keys() & actual.keys():
        want, got = contract[col], actual[col]
        if want.type != got.type:
            safe = (want.type, got.type) in SAFE_WIDENING
            out.append(Change(col, "type", f"{want.type} -> {got.type}",
                              Severity.WARN if safe else Severity.BREAK))
        if got.nullable and not want.nullable:
            out.append(Change(col, "nulls", "nulls in NOT NULL column", Severity.BREAK))
    return sorted(out, key=lambda c: (c.severity != Severity.BREAK, c.column))


def exit_code(changes: list[Change]) -> int:
    """0 = clean, 1 = warnings only, 2 = breaking change (stop the pipeline)."""
    if any(c.severity == Severity.BREAK for c in changes):
        return 2
    return 1 if changes else 0
