"""Lightweight TF-IDF embedder (stdlib only) for offline retrieval.

Swap path (optional, not required for tests): set OLLAMA_BASE_URL and call
an Ollama embeddings endpoint from a future OllamaEmbedder class.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class TfidfEmbedder:
    """Fit on a corpus, then encode queries/docs as sparse TF-IDF vectors."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: list[float] = []
        self._fitted = False

    def fit(self, documents: Iterable[str]) -> TfidfEmbedder:
        docs = [tokenize(d) for d in documents]
        if not docs:
            raise ValueError("Cannot fit on empty corpus")
        df: Counter[str] = Counter()
        for tokens in docs:
            df.update(set(tokens))
        terms = sorted(df.keys())
        self.vocab = {t: i for i, t in enumerate(terms)}
        n = len(docs)
        self.idf = [math.log((1 + n) / (1 + df[t])) + 1.0 for t in terms]
        self._fitted = True
        return self

    def transform(self, text: str) -> list[float]:
        if not self._fitted:
            raise RuntimeError("Call fit() before transform()")
        tokens = tokenize(text)
        if not tokens:
            return [0.0] * len(self.vocab)
        tf = Counter(tokens)
        total = len(tokens)
        vec = [0.0] * len(self.vocab)
        for term, count in tf.items():
            idx = self.vocab.get(term)
            if idx is None:
                continue
            vec[idx] = (count / total) * self.idf[idx]
        return self._l2_normalize(vec)

    def fit_transform(self, documents: Iterable[str]) -> list[list[float]]:
        docs = list(documents)
        self.fit(docs)
        return [self.transform(d) for d in docs]

    @staticmethod
    def _l2_normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity for equal-length L2-normalized (or raw) vectors."""
    if len(a) != len(b):
        raise ValueError("Vector length mismatch")
    return sum(x * y for x, y in zip(a, b))
