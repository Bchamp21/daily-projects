from hybrid.corpus import DOCS
from hybrid.search import HybridSearch

hs = HybridSearch(DOCS)
for q in ["NVDA earnings", "Microsoft cloud forecast", "Tesla Autopilot recall"]:
    print(f"\nQ: {q}")
    print("  BM25  :", [d for d, _ in hs.bm25.search(q, 3)])
    print("  Vector:", [d for d, _ in hs.vec.search(q, 3)])
    for d in hs.search(q):
        print(f"  HYBRID {d}: {DOCS[d]}")
