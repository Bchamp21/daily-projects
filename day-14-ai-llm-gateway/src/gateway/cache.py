"""Semantic cache: reuse an answer when a new prompt *means* the same thing."""
import time
from dataclasses import dataclass, field

from .embed import cosine, embed


@dataclass
class Entry:
    prompt: str
    vector: list[float]
    answer: str
    created: float = field(default_factory=time.time)


class SemanticCache:
    def __init__(self, threshold: float = 0.85, ttl_seconds: float = 3600, max_items: int = 500, clock=time.time):
        self.threshold = threshold
        self.ttl = ttl_seconds
        self.max_items = max_items
        self.clock = clock
        self.entries: list[Entry] = []

    def get(self, prompt: str) -> tuple[str | None, float]:
        """Return (answer, similarity) for the best fresh match, or (None, best_score)."""
        now = self.clock()
        self.entries = [e for e in self.entries if now - e.created < self.ttl]  # expire
        if not self.entries:
            return None, 0.0
        q = embed(prompt)
        best = max(self.entries, key=lambda e: cosine(q, e.vector))
        score = cosine(q, best.vector)
        return (best.answer, score) if score >= self.threshold else (None, score)

    def put(self, prompt: str, answer: str) -> None:
        self.entries.append(Entry(prompt, embed(prompt), answer, self.clock()))
        if len(self.entries) > self.max_items:  # evict oldest
            self.entries.pop(0)
