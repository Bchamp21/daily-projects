"""Semantic cache for LLM calls.

Exact hit  -> normalized prompt string matches.
Semantic   -> cosine >= threshold AND the 'entities' (tickers, numbers, dates) match.
Miss       -> call the LLM, store the answer with a TTL.
"""
import re
import time
from dataclasses import dataclass, field

from embed import cosine, tokens

TICKER = re.compile(r"\b[A-Z]{2,5}\b")
NUMBER = re.compile(r"\b\d+(?:[.,/-]\d+)*\b")
NOT_TICKERS = {"AI", "LLM", "USD", "ETF", "CEO", "API", "EPS", "WHAT", "THE", "HOW"}


def normalize(prompt: str) -> str:
    return " ".join(tokens(prompt))


def entities(prompt: str) -> frozenset:
    """Things that must match exactly: 'AAPL close' != 'MSFT close'."""
    t = {x for x in TICKER.findall(prompt) if x not in NOT_TICKERS}
    n = set(NUMBER.findall(prompt))
    return frozenset(t | n)


@dataclass
class Entry:
    prompt: str
    key: str
    vec: list[float]
    ents: frozenset
    answer: str
    created: float
    hits: int = 0


@dataclass
class Stats:
    exact: int = 0
    semantic: int = 0
    miss: int = 0
    blocked_by_entity: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.exact + self.semantic + self.miss
        return (self.exact + self.semantic) / total if total else 0.0


@dataclass
class SemanticCache:
    embedder: object
    llm: object
    threshold: float = 0.85
    ttl_s: float = 3600
    max_entries: int = 1000
    clock: object = time.monotonic
    entries: list = field(default_factory=list)
    stats: Stats = field(default_factory=Stats)

    def _expire(self):
        now = self.clock()
        self.entries = [e for e in self.entries if now - e.created < self.ttl_s]

    def lookup(self, prompt: str):
        """Return (answer, kind, score) or (None, 'miss', best_score)."""
        self._expire()
        key, ents = normalize(prompt), entities(prompt)
        for e in self.entries:
            if e.key == key and e.ents == ents:
                e.hits += 1
                self.stats.exact += 1
                return e.answer, "exact", 1.0
        vec = self.embedder.embed(prompt)
        best, best_s = None, -1.0
        for e in self.entries:
            s = cosine(vec, e.vec)
            if s > best_s:
                best, best_s = e, s
        if best is not None and best_s >= self.threshold:
            if best.ents != ents:
                self.stats.blocked_by_entity += 1  # looks similar, different stock/date
            else:
                best.hits += 1
                self.stats.semantic += 1
                return best.answer, "semantic", best_s
        self.stats.miss += 1
        return None, "miss", best_s

    def ask(self, prompt: str) -> dict:
        answer, kind, score = self.lookup(prompt)
        if answer is None:
            answer = self.llm.complete(prompt)
            self.put(prompt, answer)
        return {"answer": answer, "cache": kind, "score": round(score, 3)}

    def put(self, prompt: str, answer: str):
        if len(self.entries) >= self.max_entries:  # evict least used, then oldest
            self.entries.sort(key=lambda e: (e.hits, e.created))
            self.entries.pop(0)
        self.entries.append(Entry(prompt, normalize(prompt), self.embedder.embed(prompt),
                                  entities(prompt), answer, self.clock()))

    def invalidate(self, entity: str) -> int:
        """New data for a ticker arrived: drop every cached answer mentioning it."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if entity not in e.ents]
        return before - len(self.entries)
