"""Tiny offline embedding: hashed bag of words + character trigrams.

Good enough to show the idea of a semantic cache. Swap for a real model
(e.g. Ollama `nomic-embed-text`) in production.
"""
import hashlib
import math
import re

DIM = 256
STOP = {"the", "a", "an", "is", "of", "for", "to", "what", "was", "me", "please", "tell", "show", "s"}


def _tokens(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]
    grams = [w[i:i + 3] for w in words for i in range(max(1, len(w) - 2))]
    return words + grams


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0 if (h >> 8) % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
