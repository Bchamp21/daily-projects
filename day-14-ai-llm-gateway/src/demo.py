"""Run: python src/demo.py   (offline). Set USE_GROQ=1 with GROQ_API_KEY for a real model."""
import os

from gateway import EchoProvider, FlakyProvider, Gateway, SemanticCache
from gateway.providers import GroqProvider

primary = GroqProvider() if os.environ.get("USE_GROQ") else FlakyProvider(fail_times=1, name="primary", cost_per_1k_tokens=0.5)
gw = Gateway([primary, EchoProvider(name="backup", cost_per_1k_tokens=0.1)], SemanticCache(threshold=0.8))

prompts = [
    "What was AAPL closing price trend this week?",
    "AAPL closing price trend this week",
    "Summarize MSFT earnings news",
    "Tell me the AAPL closing price trend this week please",
]
for q in prompts:
    r = gw.ask(q)
    print(f"{r.source:8} sim={r.similarity:.2f} cost=${r.est_cost:.5f}  {q}")
print(f"\nhit rate {gw.hit_rate():.0%}, fallbacks {gw.stats['fallbacks']}, total cost ${gw.stats['cost']:.5f}")
