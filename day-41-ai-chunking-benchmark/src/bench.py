"""Benchmark chunking strategies on the same docs + questions."""
from dataclasses import dataclass
from retriever import make_index

def _norm(s: str) -> str:
    return " ".join(s.lower().split())

@dataclass
class Result:
    name: str
    n_chunks: int
    hit_rate: float      # share of questions whose answer sits whole inside a top-k chunk
    mrr: float           # 1/rank of the first chunk holding the answer (0 if none)
    ctx_chars: float     # avg characters sent to the LLM per question (cost)

def evaluate(name, chunker, docs, qa, k=3) -> Result:
    chunks = [c for d in docs for c in chunker(d)]
    idx = make_index(chunks)
    hits, rr, chars = 0, 0.0, 0
    for question, answer in qa:
        top = idx.search(question, k)
        chars += sum(len(chunks[i]) for i, _ in top)
        for rank, (i, _) in enumerate(top, 1):
            if _norm(answer) in _norm(chunks[i]):
                hits += 1; rr += 1 / rank
                break
    n = len(qa) or 1
    return Result(name, len(chunks), hits / n, rr / n, chars / n)

def pick_best(results: list[Result]) -> Result:
    """Most answers found, then best rank, then cheapest context."""
    return sorted(results, key=lambda r: (-r.hit_rate, -r.mrr, r.ctx_chars))[0]

def table(results: list[Result]) -> str:
    lines = ["| strategy | chunks | hit@k | MRR | ctx chars |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.name} | {r.n_chunks} | {r.hit_rate:.0%} | {r.mrr:.2f} | {r.ctx_chars:.0f} |")
    return "\n".join(lines)
