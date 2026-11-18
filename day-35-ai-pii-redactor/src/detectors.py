"""PII detectors: regex finds candidates, validators cut false positives."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    kind: str
    start: int
    end: int
    text: str


def luhn_ok(digits: str) -> bool:
    """Credit-card checksum. Rejects random 16-digit numbers like order ids."""
    nums = [int(d) for d in digits if d.isdigit()]
    if not 13 <= len(nums) <= 19:
        return False
    total = 0
    for i, n in enumerate(reversed(nums)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def ssn_ok(text: str) -> bool:
    area, group, serial = text.split("-")
    return area not in ("000", "666") and not area.startswith("9") and group != "00" and serial != "0000"


# order matters: earlier kinds win when spans overlap
PATTERNS = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), None),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), ssn_ok),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b"), luhn_ok),
    ("PHONE", re.compile(r"(?<!\w)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}\b"), None),
    ("ACCOUNT", re.compile(r"\b(?:acct|account)\s*(?:#|no\.?|number)?\s*:?\s*(\d{6,12})\b", re.I), None),
]


def find_pii(text: str, allow: set[str] | None = None) -> list[Span]:
    """All PII spans, no overlaps, sorted by position. 'allow' = values never redacted."""
    allow = allow or set()
    found: list[Span] = []
    for kind, rx, check in PATTERNS:
        for m in rx.finditer(text):
            # ACCOUNT: redact only the number, keep the word 'account'
            g = 1 if m.groups() else 0
            s, e = m.start(g), m.end(g)
            val = text[s:e].strip()
            e = s + len(val)
            if val in allow or (check and not check(val)):
                continue
            if any(s < f.end and f.start < e for f in found):
                continue
            found.append(Span(kind, s, e, val))
    return sorted(found, key=lambda x: x.start)
