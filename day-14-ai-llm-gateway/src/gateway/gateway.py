"""LLM gateway: cache first, then providers in order with fallback, plus usage stats."""
import time
from dataclasses import dataclass

from .cache import SemanticCache
from .providers import Provider, ProviderError


@dataclass
class Result:
    answer: str
    source: str          # "cache" or provider name
    similarity: float
    latency_ms: float
    est_cost: float


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough rule of thumb: ~4 chars per token


class Gateway:
    def __init__(self, providers: list[Provider], cache: SemanticCache | None = None):
        if not providers:
            raise ValueError("need at least one provider")
        self.providers = providers
        self.cache = cache or SemanticCache()
        self.stats = {"requests": 0, "cache_hits": 0, "fallbacks": 0, "errors": [], "cost": 0.0}

    def ask(self, prompt: str) -> Result:
        start = time.perf_counter()
        self.stats["requests"] += 1

        hit, score = self.cache.get(prompt)
        if hit is not None:
            self.stats["cache_hits"] += 1
            return Result(hit, "cache", score, (time.perf_counter() - start) * 1000, 0.0)

        for i, p in enumerate(self.providers):
            try:
                answer = p.complete(prompt)
            except ProviderError as e:
                self.stats["errors"].append(f"{p.name}: {e}")
                continue
            if i > 0:
                self.stats["fallbacks"] += 1
            cost = (est_tokens(prompt) + est_tokens(answer)) / 1000 * p.cost_per_1k_tokens
            self.stats["cost"] += cost
            self.cache.put(prompt, answer)
            return Result(answer, p.name, score, (time.perf_counter() - start) * 1000, cost)

        raise ProviderError("all providers failed: " + "; ".join(self.stats["errors"][-len(self.providers):]))

    def hit_rate(self) -> float:
        return self.stats["cache_hits"] / self.stats["requests"] if self.stats["requests"] else 0.0
