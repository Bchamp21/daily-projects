"""Day 28: Delta Change Data Feed (CDF) -> incremental Gold.

DeltaTable  : a tiny in-memory stand-in for a Silver Delta table with CDF on.
              Every commit gets a version; every row change is logged as
              insert / update_preimage / update_postimage / delete.
CdfConsumer : reads changes after its checkpoint version and folds them into
              Gold (per-ticker row_count, sum_close, avg_close) without
              re-reading the whole Silver table.
"""
from __future__ import annotations

from dataclasses import dataclass, field

Key = tuple[str, str]  # (ticker, trade_date)

# How each CDF change type moves the Gold totals: (count delta, close sign)
SIGN = {"insert": 1, "update_postimage": 1, "update_preimage": -1, "delete": -1}


@dataclass
class DeltaTable:
    rows: dict[Key, float] = field(default_factory=dict)
    changes: list[dict] = field(default_factory=list)
    version: int = 0

    def commit(self, upserts: dict[Key, float] | None = None,
               deletes: list[Key] | None = None) -> int:
        """One atomic commit = one new version (like a Delta MERGE)."""
        self.version += 1
        v = self.version
        for key, close in (upserts or {}).items():
            old = self.rows.get(key)
            if old is None:
                self._log(v, "insert", key, close)
            elif old != close:
                self._log(v, "update_preimage", key, old)
                self._log(v, "update_postimage", key, close)
            self.rows[key] = close
        for key in deletes or []:
            if key in self.rows:
                self._log(v, "delete", key, self.rows.pop(key))
        return v

    def _log(self, v: int, ctype: str, key: Key, close: float) -> None:
        self.changes.append({"ticker": key[0], "trade_date": key[1], "close": close,
                             "_change_type": ctype, "_commit_version": v})

    def table_changes(self, starting_version: int) -> list[dict]:
        """Like SQL table_changes('silver', starting_version)."""
        return [c for c in self.changes if c["_commit_version"] >= starting_version]


@dataclass
class CdfConsumer:
    checkpoint: int = 0  # last version already applied to Gold
    gold: dict[str, dict] = field(default_factory=dict)

    def run(self, table: DeltaTable) -> int:
        """Apply new changes once. Returns how many change rows were used."""
        changes = table.table_changes(self.checkpoint + 1)
        for c in changes:
            sign = SIGN[c["_change_type"]]
            g = self.gold.setdefault(c["ticker"], {"row_count": 0, "sum_close": 0.0})
            g["row_count"] += sign
            g["sum_close"] = round(g["sum_close"] + sign * c["close"], 6)
        for t in [t for t, g in self.gold.items() if g["row_count"] == 0]:
            del self.gold[t]
        for g in self.gold.values():
            g["avg_close"] = round(g["sum_close"] / g["row_count"], 4)
        if changes:
            self.checkpoint = max(c["_commit_version"] for c in changes)
        return len(changes)


def full_recompute(table: DeltaTable) -> dict[str, dict]:
    """The slow way: scan all of Silver. Used to prove incremental == full."""
    gold: dict[str, dict] = {}
    for (ticker, _), close in table.rows.items():
        g = gold.setdefault(ticker, {"row_count": 0, "sum_close": 0.0})
        g["row_count"] += 1
        g["sum_close"] = round(g["sum_close"] + close, 6)
    for g in gold.values():
        g["avg_close"] = round(g["sum_close"] / g["row_count"], 4)
    return gold
