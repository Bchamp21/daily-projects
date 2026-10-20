"""Retrieval and groundedness metrics. All return values between 0 and 1."""
from .retrievers import tokens


def hit_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """1 if any relevant doc is in the top k, else 0."""
    return 1.0 if set(retrieved[:k]) & set(relevant) else 0.0


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Share of the relevant docs found in the top k."""
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & set(relevant)) / len(set(relevant))


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    """1/rank of the first relevant doc (1.0 if first, 0.5 if second, 0 if missing)."""
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def groundedness(answer: str, sources: list[str], min_overlap: float = 0.6) -> float:
    """Share of answer sentences whose words mostly appear in some source.

    A cheap, offline stand-in for an LLM judge's faithfulness score.
    """
    sentences = [s.strip() for s in answer.replace("!", ".").split(".") if s.strip()]
    if not sentences:
        return 0.0
    source_sets = [set(tokens(s)) for s in sources]
    supported = 0
    for sent in sentences:
        words = set(tokens(sent))
        if not words:
            supported += 1
            continue
        best = max((len(words & src) / len(words) for src in source_sets), default=0.0)
        if best >= min_overlap:
            supported += 1
    return supported / len(sentences)
