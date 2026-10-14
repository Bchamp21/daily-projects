"""CLI: ask a question against the sample stock-news corpus."""

from __future__ import annotations

import argparse
import sys

from stock_rag.answer import answer_question
from stock_rag.retriever import NewsRetriever


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Day 2 AI: offline RAG over sample AAPL/MSFT/NVDA headlines",
    )
    p.add_argument(
        "question",
        nargs="?",
        default="Why is NVDA mentioned in AI earnings?",
        help='Question to ask (default: "Why is NVDA mentioned in AI earnings?")',
    )
    p.add_argument("-k", type=int, default=3, help="Top-k headlines to retrieve")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    retriever = NewsRetriever()
    result = answer_question(args.question, retriever=retriever, k=args.k)
    print(f"mode: {result['mode']}")
    print(result["answer"])
    if result.get("citations"):
        print("\ncitations:")
        for c in result["citations"]:
            print(f"  - {c['id']} {c['ticker']}: {c['headline']} (score={c['score']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
