import pytest

from cache import SemanticCache, entities, normalize
from embed import HashEmbedder
from llm import FakeLLM


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def cache():
    return SemanticCache(HashEmbedder(), FakeLLM(), threshold=0.6, clock=Clock())


def test_normalize_drops_case_punct_stopwords():
    assert normalize("What is the AAPL close?") == normalize("aapl CLOSE")


def test_entities_tickers_and_dates():
    assert entities("AAPL close on 2026-11-10") == frozenset({"AAPL", "2026-11-10"})
    assert "AI" not in entities("AI news for NVDA")


def test_miss_then_exact_hit_saves_llm_call(cache):
    q = "What was the AAPL close on 2026-11-10?"
    assert cache.ask(q)["cache"] == "miss"
    r = cache.ask(q)
    assert r["cache"] == "exact" and cache.llm.calls == 1


def test_paraphrase_is_semantic_hit(cache):
    cache.ask("What was the AAPL close on 2026-11-10?")
    r = cache.ask("Tell me the AAPL closing price on 2026-11-10 please")
    assert r["cache"] == "semantic"
    assert cache.llm.calls == 1


def test_different_ticker_never_served(cache):
    cache.ask("What was the AAPL close on 2026-11-10?")
    r = cache.ask("What was the MSFT close on 2026-11-10?")
    assert r["cache"] == "miss" and cache.llm.calls == 2
    assert "MSFT" in r["answer"]


def test_different_date_blocked_by_entity_check(cache):
    cache.ask("What was the AAPL close on 2026-11-10?")
    r = cache.ask("What was the AAPL close on 2026-11-09?")
    assert r["cache"] == "miss"
    assert cache.stats.blocked_by_entity == 1


def test_unrelated_question_misses(cache):
    cache.ask("What was the AAPL close on 2026-11-10?")
    assert cache.ask("Explain a Delta Lake MERGE")["cache"] == "miss"


def test_ttl_expiry(cache):
    q = "AAPL close 2026-11-10"
    cache.ask(q)
    cache.clock.t = cache.ttl_s + 1
    assert cache.ask(q)["cache"] == "miss" and cache.llm.calls == 2


def test_invalidate_by_ticker(cache):
    cache.ask("AAPL close 2026-11-10")
    cache.ask("NVDA close 2026-11-10")
    assert cache.invalidate("AAPL") == 1
    assert cache.ask("AAPL close 2026-11-10")["cache"] == "miss"
    assert cache.ask("NVDA close 2026-11-10")["cache"] == "exact"


def test_eviction_keeps_hot_entry():
    c = SemanticCache(HashEmbedder(), FakeLLM(), max_entries=2, clock=Clock())
    c.ask("AAPL close 2026-11-10")
    c.ask("AAPL close 2026-11-10")  # hot
    c.ask("NVDA volume 2026-11-10")
    c.ask("TSLA dividend 2026")       # evicts NVDA (0 hits)
    assert c.ask("AAPL close 2026-11-10")["cache"] == "exact"


def test_hit_rate(cache):
    cache.ask("AAPL close 2026-11-10")
    cache.ask("AAPL close 2026-11-10")
    assert cache.stats.hit_rate == 0.5
