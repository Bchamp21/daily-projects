"""CLI: python -m rag_evals [--k 3] [--min-mrr 0.7] [--report report.json]"""
import argparse
import json
import sys

from .data import load_docs, load_golden
from .retrievers import KeywordRetriever, TfidfRetriever
from .runner import evaluate, passes_gate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Evaluate two RAG retrievers on a golden set.")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--min-mrr", type=float, default=0.7, help="fail (exit 1) below this MRR")
    p.add_argument("--report", default=None, help="write full results to this JSON file")
    args = p.parse_args(argv)

    docs, golden = load_docs(), load_golden()
    results = {}
    for name, cls in [("keyword", KeywordRetriever), ("tfidf", TfidfRetriever)]:
        results[name] = evaluate(cls(docs), golden, docs, k=args.k)

    metrics = list(results["tfidf"]["summary"].keys())
    print(f"{'metric':<14}" + "".join(f"{n:>10}" for n in results))
    for m in metrics:
        print(f"{m:<14}" + "".join(f"{results[n]['summary'][m]:>10}" for n in results))
    for n, r in results.items():
        if r["failures"]:
            print(f"\n{n} missed: " + "; ".join(r["failures"]))

    if args.report:
        with open(args.report, "w") as f:
            json.dump(results, f, indent=2)

    ok = passes_gate(results["tfidf"]["summary"], args.min_mrr)
    print(f"\nGate (tfidf MRR >= {args.min_mrr}): {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
