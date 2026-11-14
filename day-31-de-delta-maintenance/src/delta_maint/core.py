"""Delta table maintenance planner: OPTIMIZE (bin-packing small files) + safe VACUUM.

A fake Delta log of files lets us test the logic locally. The same decisions map
1:1 to Databricks SQL (see render_sql and the databricks/ folder).
"""
from __future__ import annotations

from dataclasses import dataclass, field

MB = 1024 * 1024
DEFAULT_TARGET = 128 * MB
MIN_SAFE_RETENTION_HOURS = 168  # Delta default: 7 days


@dataclass
class DataFile:
    path: str
    size: int
    partition: str
    added_at: float          # hours since epoch (simple clock for tests)
    removed_at: float | None = None  # set = tombstoned (still on storage)

    @property
    def active(self) -> bool:
        return self.removed_at is None


@dataclass
class DeltaTable:
    name: str
    files: list[DataFile] = field(default_factory=list)
    version: int = 0
    _seq: int = 0

    def add(self, partition: str, size: int, now: float) -> DataFile:
        self._seq += 1
        f = DataFile(f"{partition}/part-{self._seq:05d}.parquet", size, partition, now)
        self.files.append(f)
        self.version += 1
        return f

    def active_files(self) -> list[DataFile]:
        return [f for f in self.files if f.active]

    def rows_bytes(self) -> int:
        return sum(f.size for f in self.active_files())


@dataclass
class Health:
    file_count: int
    avg_mb: float
    small_ratio: float
    tombstones: int
    recommend_optimize: bool


def health(table: DeltaTable, target: int = DEFAULT_TARGET, small_frac: float = 0.25,
           max_small_ratio: float = 0.3) -> Health:
    act = table.active_files()
    small = [f for f in act if f.size < target * small_frac]
    n = len(act)
    ratio = len(small) / n if n else 0.0
    return Health(
        file_count=n,
        avg_mb=round(sum(f.size for f in act) / n / MB, 2) if n else 0.0,
        small_ratio=round(ratio, 3),
        tombstones=sum(1 for f in table.files if not f.active),
        recommend_optimize=ratio > max_small_ratio,
    )


@dataclass
class Bin:
    partition: str
    files: list[DataFile]

    @property
    def size(self) -> int:
        return sum(f.size for f in self.files)


def plan_optimize(table: DeltaTable, target: int = DEFAULT_TARGET,
                  where_partitions: set[str] | None = None) -> list[Bin]:
    """Bin-pack small files per partition (first-fit decreasing).

    Rules (like Delta OPTIMIZE):
    - never mix partitions
    - files already >= target are left alone
    - a bin with a single file is skipped (rewriting it gains nothing)
    """
    by_part: dict[str, list[DataFile]] = {}
    for f in table.active_files():
        if f.size >= target:
            continue
        if where_partitions is not None and f.partition not in where_partitions:
            continue
        by_part.setdefault(f.partition, []).append(f)

    bins: list[Bin] = []
    for part in sorted(by_part):
        open_bins: list[Bin] = []
        for f in sorted(by_part[part], key=lambda x: (-x.size, x.path)):
            for b in open_bins:
                if b.size + f.size <= target:
                    b.files.append(f)
                    break
            else:
                open_bins.append(Bin(part, [f]))
        bins.extend(b for b in open_bins if len(b.files) > 1)
    return bins


def apply_optimize(table: DeltaTable, bins: list[Bin], now: float) -> int:
    """Rewrite each bin as one file in ONE commit. Old files become tombstones."""
    if not bins:
        return 0
    for b in bins:
        for f in b.files:
            f.removed_at = now
        table._seq += 1
        table.files.append(DataFile(f"{b.partition}/part-{table._seq:05d}.parquet",
                                    b.size, b.partition, now))
    table.version += 1
    return len(bins)


class UnsafeRetention(ValueError):
    pass


def plan_vacuum(table: DeltaTable, now: float, retain_hours: float = MIN_SAFE_RETENTION_HOURS,
                longest_reader_hours: float = 0.0, allow_unsafe: bool = False) -> list[DataFile]:
    """Pick tombstoned files older than the retention window.

    Guards:
    - retention below 7 days needs allow_unsafe (breaks time travel / slow readers)
    - retention must always be longer than the longest running reader/stream
    - active files are never deleted
    """
    if retain_hours < longest_reader_hours:
        raise UnsafeRetention(
            f"retain {retain_hours}h < longest reader {longest_reader_hours}h: "
            "a running query could lose files")
    if retain_hours < MIN_SAFE_RETENTION_HOURS and not allow_unsafe:
        raise UnsafeRetention(
            f"retain {retain_hours}h < {MIN_SAFE_RETENTION_HOURS}h safety minimum")
    cutoff = now - retain_hours
    return [f for f in table.files if not f.active and f.removed_at <= cutoff]


def apply_vacuum(table: DeltaTable, doomed: list[DataFile]) -> int:
    ids = {id(f) for f in doomed}
    assert all(not f.active for f in doomed), "VACUUM must never delete active files"
    table.files = [f for f in table.files if id(f) not in ids]
    return len(doomed)


def render_sql(table: str, bins: list[Bin], retain_hours: float,
               cluster_by: list[str] | None = None) -> str:
    lines = [f"-- maintenance plan for {table}"]
    if cluster_by:
        lines.append(f"ALTER TABLE {table} CLUSTER BY ({', '.join(cluster_by)});")
        lines.append(f"OPTIMIZE {table};  -- liquid clustering: no ZORDER/partition filter")
    elif bins:
        parts = sorted({b.partition for b in bins})
        in_list = ", ".join(f"'{p.split('=', 1)[-1]}'" for p in parts)
        col = parts[0].split("=", 1)[0] if "=" in parts[0] else "partition"
        lines.append(f"OPTIMIZE {table} WHERE {col} IN ({in_list});")
    lines.append(f"VACUUM {table} RETAIN {int(retain_hours)} HOURS;")
    return "\n".join(lines)
