"""Tiny offline TF-IDF retriever (cosine). Swap in Ollama embeddings with USE_OLLAMA=1."""
import math, os, re
from collections import Counter

_TOK = re.compile(r"[a-z0-9$%.]+")
STOP = set("the a an of to in on and or is are was were for with by at as it its this that what how did does do from".split())

def tokens(text: str) -> list[str]:
    return [t.strip(".") for t in _TOK.findall(text.lower()) if t.strip(".") and t.strip(".") not in STOP]

class TfidfIndex:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        docs = [Counter(tokens(c)) for c in chunks]
        df = Counter(t for d in docs for t in d)
        n = len(chunks)
        self.idf = {t: math.log((1 + n) / (1 + f)) + 1 for t, f in df.items()}
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, counts: Counter) -> dict:
        v = {t: c * self.idf.get(t, 0.0) for t, c in counts.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def search(self, query: str, k: int = 3) -> list[tuple[int, float]]:
        q = self._vec(Counter(tokens(query)))
        scores = [(i, sum(w * v.get(t, 0.0) for t, w in q.items())) for i, v in enumerate(self.vecs)]
        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores[:k]

class OllamaIndex:
    """Same interface, real embeddings. Needs Ollama at OLLAMA_URL (default localhost)."""
    def __init__(self, chunks, model="nomic-embed-text"):
        import requests
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/embeddings"
        self.model, self.req, self.chunks = model, requests, chunks
        self.vecs = [self._emb(c) for c in chunks]

    def _emb(self, text):
        v = self.req.post(self.url, json={"model": self.model, "prompt": text}, timeout=60).json()["embedding"]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def search(self, query, k=3):
        q = self._emb(query)
        s = sorted(((i, sum(a * b for a, b in zip(q, v))) for i, v in enumerate(self.vecs)), key=lambda x: (-x[1], x[0]))
        return s[:k]

def make_index(chunks):
    return OllamaIndex(chunks) if os.environ.get("USE_OLLAMA") == "1" else TfidfIndex(chunks)
