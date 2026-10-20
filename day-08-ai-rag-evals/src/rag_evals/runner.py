"""Run every golden question through a retriever, score it, and gate on quality."""
from statistics import mean

from .metrics import groundedness, hit_at_k, recall_at_k, reciprocal_rank


def extractive_answer(doc_ids: list[str], docs_by_id: dict[str, dict]) -> str:
    """Answer by quoting the top doc (offline, so it can't make things up)."""
    if not doc_ids:
        return "I don't know."
    return docs_by_id[doc_ids[0]]["text"]


def evaluate(retriever, golden: list[dict], docs: list[dict], k: int = 3) -> dict:
    docs_by_id = {d["id"]: d for d in docs}
    rows = []
    for g in golden:
        got = retriever.search(g["question"], k=k)
        answer = extractive_answer(got, docs_by_id)
        sources = [docs_by_id[i]["text"] for i in got]
        rows.append({
            "question": g["question"],
            "retrieved": got,
            "relevant": g["relevant"],
            "hit": hit_at_k(got, g["relevant"], k),
            "recall": recall_at_k(got, g["relevant"], k),
            "rr": reciprocal_rank(got, g["relevant"]),
            # "I don't know" makes nothing up, so it counts as grounded.
            "grounded": 1.0 if not got else groundedness(answer, sources),
        })
    summary = {
        f"hit@{k}": round(mean(r["hit"] for r in rows), 3),
        f"recall@{k}": round(mean(r["recall"] for r in rows), 3),
        "mrr": round(mean(r["rr"] for r in rows), 3),
        "groundedness": round(mean(r["grounded"] for r in rows), 3),
    }
    failures = [r["question"] for r in rows if r["hit"] == 0]
    return {"summary": summary, "failures": failures, "rows": rows}


def passes_gate(summary: dict, min_mrr: float) -> bool:
    return summary["mrr"] >= min_mrr
