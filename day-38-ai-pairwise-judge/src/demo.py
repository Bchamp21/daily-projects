import os
from arena import run, wilson
from judges import HeuristicJudge, OllamaJudge

DATA = [
    {"id": "q1", "q": "What was AAPL close on 2026-11-20?", "ref": "AAPL closed 228.40 on 2026-11-20",
     "new": "AAPL closed at 228.40 on 2026-11-20.", "old": "Apple stock did well recently."},
    {"id": "q2", "q": "Which ticker had the highest volume?", "ref": "NVDA 412M shares",
     "new": "NVDA, with 412M shares.", "old": "NVDA had the highest volume."},
    {"id": "q3", "q": "MSFT 5-day return?", "ref": "MSFT 5-day return 2.1%",
     "new": "MSFT returned 2.1% over 5 days.", "old": "MSFT returned 2.1% over 5 days."},
    {"id": "q4", "q": "Did TSLA beat earnings?", "ref": "TSLA missed EPS 0.62 vs 0.70",
     "new": "TSLA missed: EPS 0.62 vs 0.70 expected.", "old": "Yes TSLA beat."},
]

if __name__ == "__main__":
    judge = OllamaJudge() if os.getenv("USE_OLLAMA") else HeuristicJudge(position_bias=0.0)
    rep = run(judge, DATA)
    for r in rep.results:
        print(f"{r.qid}: first={r.first} swapped={r.second} -> {r.final} (consistent={r.consistent})")
    lo, hi = wilson(rep.count("new") + 0.5 * rep.count("tie"), rep.n)
    print(f"win rate {rep.win_rate:.0%}  95% CI [{lo:.0%}, {hi:.0%}]  consistency {rep.consistency:.0%}")
    print("decision:", rep.decision())

