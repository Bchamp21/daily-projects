"""Two retrievers to compare: plain keyword overlap vs TF-IDF cosine."""
import math
import re
from collections import Counter

STOP = {"the", "a", "an", "is", "of", "to", "on", "in", "as", "and", "its", "for",
        "how", "what", "which", "who", "why", "are", "with", "me", "about", "tell",
        "doing", "their", "by", "into", "it", "at", "from", "much", "did", "up", "down"}


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOP]


class KeywordRetriever:
    """Baseline: score = number of shared words."""

    def __init__(self, docs: list[dict]):
        self.docs = docs
        self.doc_tokens = [set(tokens(d["text"] + " " + d["ticker"])) for d in docs]

    def search(self, query: str, k: int = 3) -> list[str]:
        q = set(tokens(query))
        scored = [(len(q & dt), i) for i, dt in enumerate(self.doc_tokens)]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [self.docs[i]["id"] for _, i in scored[:k]]


class TfidfRetriever:
    """Rare words count more (IDF), then rank by cosine similarity."""

    def __init__(self, docs: list[dict]):
        self.docs = docs
        toks = [tokens(d["text"] + " " + d["ticker"]) for d in docs]
        n = len(docs)
        df = Counter(w for t in toks for w in set(t))
        self.idf = {w: math.log((1 + n) / (1 + c)) + 1 for w, c in df.items()}
        self.vecs = [self._vec(t) for t in toks]

    def _vec(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        v = {w: c * self.idf.get(w, 0.0) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    def search(self, query: str, k: int = 3) -> list[str]:
        q = self._vec(tokens(query))
        scored = []
        for i, dv in enumerate(self.vecs):
            s = sum(q[w] * dv.get(w, 0.0) for w in q)
            if s > 0:
                scored.append((s, i))
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [self.docs[i]["id"] for _, i in scored[:k]]
