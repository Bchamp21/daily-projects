"""Vector search. Offline: hashed bag-of-normalized-words embeddings.
Optional: real embeddings from local Ollama (set USE_OLLAMA=1, OLLAMA_HOST, OLLAMA_EMBED_MODEL)."""
import hashlib
import math
import os

from .text import normalize, tokenize

DIM = 256


def hashed_embed(text: str, dim: int = DIM) -> list[float]:
    v = [0.0] * dim
    for t in normalize(tokenize(text)):
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        v[h % dim] += 1.0 if (h >> 8) % 2 == 0 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def ollama_embed(text: str) -> list[float]:  # pragma: no cover - needs a running Ollama
    import requests

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    r = requests.post(f"{host}/api/embeddings", json={"model": model, "prompt": text}, timeout=30)
    r.raise_for_status()
    v = r.json()["embedding"]
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # vectors are already unit length


class VectorIndex:
    def __init__(self, docs: dict[str, str], embed=None):
        self.embed = embed or (ollama_embed if os.environ.get("USE_OLLAMA") else hashed_embed)
        self.vecs = {i: self.embed(t) for i, t in docs.items()}

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        q = self.embed(query)
        scored = sorted(((i, cosine(q, v)) for i, v in self.vecs.items()), key=lambda x: -x[1])
        return [x for x in scored if x[1] > 0][:k]
