import pytest

from gateway import EchoProvider, FlakyProvider, Gateway, ProviderError, SemanticCache, cosine, embed


def test_embedding_is_normalized_and_similar_for_paraphrase():
    a, b, c = embed("AAPL closing price trend this week"), embed("what was the AAPL closing price trend this week"), embed("MSFT earnings call summary")
    assert abs(cosine(a, a) - 1.0) < 1e-9
    assert cosine(a, b) > cosine(a, c)


def test_cache_hit_on_paraphrase_and_miss_on_new_topic():
    cache = SemanticCache(threshold=0.8)
    cache.put("AAPL closing price trend this week", "up 3%")
    assert cache.get("What was the AAPL closing price trend this week?")[0] == "up 3%"
    assert cache.get("Summarize MSFT earnings news")[0] is None


def test_cache_ttl_expires():
    now = [0.0]
    cache = SemanticCache(ttl_seconds=10, clock=lambda: now[0])
    cache.put("q", "a")
    assert cache.get("q")[0] == "a"
    now[0] = 11
    assert cache.get("q")[0] is None


def test_cache_evicts_oldest():
    cache = SemanticCache(max_items=2)
    for p in ["one alpha", "two beta", "three gamma"]:
        cache.put(p, p)
    assert [e.prompt for e in cache.entries] == ["two beta", "three gamma"]


def test_gateway_second_similar_call_skips_provider():
    p = EchoProvider()
    gw = Gateway([p], SemanticCache(threshold=0.8))
    first = gw.ask("AAPL closing price trend this week")
    second = gw.ask("What was AAPL closing price trend this week?")
    assert first.source == "echo" and second.source == "cache"
    assert p.calls == 1 and gw.hit_rate() == 0.5 and second.est_cost == 0.0


def test_fallback_when_primary_fails():
    primary = FlakyProvider(fail_times=1, name="primary")
    backup = EchoProvider(name="backup")
    gw = Gateway([primary, backup])
    r = gw.ask("hello")
    assert r.source == "backup" and gw.stats["fallbacks"] == 1
    assert "primary" in gw.stats["errors"][0]


def test_all_providers_fail_raises():
    gw = Gateway([FlakyProvider(fail_times=5, name="a"), FlakyProvider(fail_times=5, name="b")])
    with pytest.raises(ProviderError, match="all providers failed"):
        gw.ask("hello")


def test_cost_tracking():
    gw = Gateway([EchoProvider(cost_per_1k_tokens=1.0)])
    r = gw.ask("x" * 400)
    assert r.est_cost > 0 and gw.stats["cost"] == pytest.approx(r.est_cost)


def test_needs_provider():
    with pytest.raises(ValueError):
        Gateway([])
