import os
from grounding import check, gate, groundedness, repair_citations
from llm import FakeJudge, OllamaJudge, judge_gray_zone

SOURCES = {
    1: "Nvidia reported quarterly revenue of 35.1 billion dollars, up 94 percent from a year ago.",
    2: "Apple shares fell 2.3 percent after iPhone sales in China declined.",
}
ANSWER = ("Nvidia reported quarterly revenue of 35.1 billion dollars [1]. "
          "Apple shares fell 2.3 percent after China iPhone sales declined [1]. "
          "Nvidia revenue rose 120 percent [1]. "
          "Analysts expect a stock split next month.")

claims = check(ANSWER, SOURCES)
judge = OllamaJudge() if os.getenv("USE_OLLAMA") else FakeJudge()
judge_gray_zone(claims, SOURCES, judge)
for c in claims:
    print(f"{c.verdict:15} score={c.score:.2f} cites={c.cites} best={c.best_source} | {c.text}")
print(f"groundedness={groundedness(claims):.0%} gate={gate(claims)}")
print("repaired:", repair_citations(claims))
