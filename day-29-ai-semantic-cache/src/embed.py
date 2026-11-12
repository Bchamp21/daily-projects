"""Embeddings. HashEmbedder is offline + deterministic (tests); OllamaEmbedder is real."""
import hashlib
import math
import os
import re

TOKEN = re.compile(r"[a-z0-9]+")
STOP = {"the", "a", "an", "of", "is", "was", "what", "for", "to", "me", "please",
        "tell", "on", "in", "did", "do", "does", "how", "much", "s"}


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


class HashEmbedder:
    """Bag-of-words hashed into a fixed vector, L2-normalized."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for t in tokens(text):
            h = int(hashlib.md5(t.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


class OllamaEmbedder:  # pragma: no cover - needs a running Ollama
    def __init__(self, model: str = "nomic-embed-text"):
        import requests
        self.requests = requests
        self.model = model
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    def embed(self, text: str) -> list[float]:
        r = self.requests.post(f"{self.url}/api/embeddings",
                               json={"model": self.model, "prompt": text}, timeout=30)
        r.raise_for_status()
        v = r.json()["embedding"]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
