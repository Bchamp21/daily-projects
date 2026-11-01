"""Reciprocal Rank Fusion and Maximal Marginal Relevance."""
from .vectors import cosine


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Each list votes 1/(k + rank). Uses ranks, not raw scores, so BM25 and cosine never need rescaling."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def mmr(query_vec, candidates: list[str], vecs: dict, top_n: int = 3, lam: float = 0.7) -> list[str]:
    """Pick relevant docs but penalize ones too similar to what we already picked."""
    picked: list[str] = []
    pool = list(candidates)
    while pool and len(picked) < top_n:
        def gain(d):
            redundancy = max((cosine(vecs[d], vecs[p]) for p in picked), default=0.0)
            return lam * cosine(query_vec, vecs[d]) - (1 - lam) * redundancy
        best = max(pool, key=gain)
        picked.append(best)
        pool.remove(best)
    return picked
