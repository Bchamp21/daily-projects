import os

from cache import SemanticCache
from embed import HashEmbedder
from llm import FakeLLM

if os.environ.get("USE_OLLAMA"):
    from embed import OllamaEmbedder
    from llm import OllamaLLM
    cache = SemanticCache(OllamaEmbedder(), OllamaLLM(), threshold=0.9)
else:
    cache = SemanticCache(HashEmbedder(), FakeLLM(), threshold=0.6)  # toy embedder needs a lower bar

questions = [
    "What was the AAPL close on 2026-11-10?",
    "what was the aapl close on 2026-11-10",        # lowercase ticker -> entity differs -> safe miss
    "Tell me the AAPL closing price on 2026-11-10",  # semantic hit
    "What was the MSFT close on 2026-11-10?",        # similar words, different ticker -> miss
    "What was the AAPL close on 2026-11-09?",        # different date -> miss
    "What was the AAPL close on 2026-11-10?",        # exact hit
]
for q in questions:
    r = cache.ask(q)
    print(f"{r['cache']:8} score={r['score']:<6} {q}")
s = cache.stats
print(f"\nLLM calls: {cache.llm.calls}/{len(questions)}  hit rate: {s.hit_rate:.0%}  "
      f"blocked by entity check: {s.blocked_by_entity}")
