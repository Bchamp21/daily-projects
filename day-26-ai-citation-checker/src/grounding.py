"""Citation checker: is every sentence in an LLM answer backed by the source it cites?"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

STOP = set("a an the of to in on for and or is are was were be by with as at from that this it its "
           "has have had will would than then into over after before about".split())
CITE = re.compile(r"\[(\d+)\]")
NUM = re.compile(r"\d+(?:\.\d+)?")

SUPPORTED, WRONG_CITATION, UNSUPPORTED, NO_CITATION = (
    "SUPPORTED", "WRONG_CITATION", "UNSUPPORTED", "NO_CITATION")


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"\d+(?:\.\d+)?|[a-z0-9]+", text.lower().replace(",", "")) if w not in STOP}


def numbers(text: str) -> set[str]:
    return set(NUM.findall(text.replace(",", "")))


@dataclass
class Claim:
    text: str
    cites: list[int]
    verdict: str = ""
    score: float = 0.0
    best_source: int | None = None
    missing_numbers: set[str] = field(default_factory=set)


def split_claims(answer: str) -> list[Claim]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", answer.strip())
    claims = []
    for p in parts:
        if not p.strip():
            continue
        cites = [int(n) for n in CITE.findall(p)]
        claims.append(Claim(re.sub(r"\s+([.!?])", r"\1", CITE.sub("", p)).strip(), cites))
    return claims


def support(claim: str, source: str) -> tuple[float, set[str]]:
    """Share of claim words found in source; 0 if any number in the claim is missing."""
    cw = words(claim) - numbers(claim)
    sw = words(source)
    overlap = len(cw & sw) / len(cw) if cw else 0.0
    missing = numbers(claim) - numbers(source)
    return (0.0 if missing else overlap), missing


def check(answer: str, sources: dict[int, str], threshold: float = 0.6) -> list[Claim]:
    claims = split_claims(answer)
    for c in claims:
        scored = {i: support(c.text, s) for i, s in sources.items()}
        best = max(scored, key=lambda i: scored[i][0]) if scored else None
        c.best_source = best
        if not c.cites:
            c.verdict = NO_CITATION
            c.score = scored[best][0] if best else 0.0
            continue
        cited = [scored[i] for i in c.cites if i in scored]
        c.score = max((s for s, _ in cited), default=0.0)
        c.missing_numbers = set().union(*(m for _, m in cited)) if cited else set()
        if c.score >= threshold:
            c.verdict = SUPPORTED
        elif best is not None and scored[best][0] >= threshold:
            c.verdict = WRONG_CITATION
        else:
            c.verdict = UNSUPPORTED
    return claims


def groundedness(claims: list[Claim]) -> float:
    return sum(c.verdict == SUPPORTED for c in claims) / len(claims) if claims else 0.0


def gate(claims: list[Claim], min_score: float = 0.8) -> str:
    """PASS, FIX (only wrong citations, can auto-repair), or BLOCK."""
    if any(c.verdict in (UNSUPPORTED, NO_CITATION) for c in claims):
        return "BLOCK" if groundedness(claims) < min_score else "FIX"
    if any(c.verdict == WRONG_CITATION for c in claims):
        return "FIX"
    return "PASS"


def repair_citations(claims: list[Claim]) -> str:
    """Re-point wrong citations to the best source; drop unsupported sentences."""
    out = []
    for c in claims:
        if c.verdict == SUPPORTED:
            out.append(f"{c.text[:-1]} [{c.cites[0]}].")
        elif c.verdict == WRONG_CITATION:
            out.append(f"{c.text[:-1]} [{c.best_source}].")
    return " ".join(out)
