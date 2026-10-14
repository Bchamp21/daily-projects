"""Top-k TF-IDF retrieval over the stock-news corpus."""

from __future__ import annotations

from typing import Any

from stock_rag.corpus import doc_text, load_corpus
from stock_rag.embedder import TfidfEmbedder, cosine_similarity


class NewsRetriever:
    def __init__(self, docs: list[dict[str, Any]] | None = None) -> None:
        self.docs = docs if docs is not None else load_corpus()
        self.embedder = TfidfEmbedder()
        corpus_texts = [doc_text(d) for d in self.docs]
        self.doc_vectors = self.embedder.fit_transform(corpus_texts)

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Return top-k docs with score, sorted highest first."""
        q = (query or "").strip()
        if not q:
            return []
        if k < 1:
            return []
        q_vec = self.embedder.transform(q)
        scored: list[tuple[float, dict[str, Any]]] = []
        for doc, vec in zip(self.docs, self.doc_vectors):
            score = cosine_similarity(q_vec, vec)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, doc in scored[:k]:
            hit = dict(doc)
            hit["score"] = round(float(score), 6)
            results.append(hit)
        return results
