import csv
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .models import PriceRow


@dataclass
class Report:
    total: int = 0
    good: list[PriceRow] = field(default_factory=list)
    bad: list[dict] = field(default_factory=list)  # {"line": n, "errors": [...]}
    duplicates: int = 0

    @property
    def pass_rate(self) -> float:
        return round(100 * len(self.good) / self.total, 1) if self.total else 0.0

    def summary(self) -> dict:
        return {
            "total_rows": self.total,
            "good_rows": len(self.good),
            "bad_rows": len(self.bad),
            "duplicates_dropped": self.duplicates,
            "pass_rate_pct": self.pass_rate,
            "errors": self.bad,
        }


def validate_rows(rows) -> Report:
    """Validate an iterable of dicts. Line numbers start at 2 (line 1 is the header)."""
    report = Report()
    seen: set[tuple[str, str]] = set()
    for line_no, raw in enumerate(rows, start=2):
        report.total += 1
        try:
            row = PriceRow(**raw)
        except ValidationError as exc:
            msgs = [f"{'.'.join(map(str, e['loc'])) or 'row'}: {e['msg']}" for e in exc.errors()]
            report.bad.append({"line": line_no, "errors": msgs})
            continue
        key = (row.symbol, row.trade_date.isoformat())
        if key in seen:
            report.duplicates += 1
            continue
        seen.add(key)
        report.good.append(row)
    return report


def validate_file(path: Path) -> Report:
    with open(path, newline="", encoding="utf-8") as f:
        return validate_rows(csv.DictReader(f))


def write_clean(report: Report, out_path: Path) -> None:
    cols = list(PriceRow.model_fields)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in report.good:
            writer.writerow(row.model_dump(mode="json"))
