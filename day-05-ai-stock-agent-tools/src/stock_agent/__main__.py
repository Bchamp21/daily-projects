import sys

from .agent import run_agent
from .llm import pick_llm

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Which did best, AAPL, MSFT or NVDA?"
    llm = pick_llm()
    out = run_agent(q, llm)
    print(f"[{type(llm).__name__}] Q: {q}")
    for t in out["trace"]:
        print(f"  tool {t['tool']}({t['args']}) -> {t['result']}")
    print("A:", out["answer"])
