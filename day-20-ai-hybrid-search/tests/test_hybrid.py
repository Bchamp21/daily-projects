import pytest

from hybrid.bm25 import BM25
from hybrid.corpus import DOCS
from hybrid.fusion import mmr, rrf
from hybrid.search import HybridSearch
from hybrid.vectors import VectorIndex, cosine, hashed_embed


@pytest.fixture(scope="module")
def hs():
    return HybridSearch(DOCS)


def test_bm25_exact_ticker_match():
    top = BM25(DOCS).search("NVDA", 5)
    assert [d for d, _ in top] == ["n1"]  # only the doc with the literal word


def test_bm25_no_match_returns_empty():
    assert BM25(DOCS).search("bitcoin", 5) == []


def test_vector_finds_synonyms_bm25_misses():
    vec_ids = [d for d, _ in VectorIndex(DOCS).search("NVDA", 5)]
    assert {"n1", "n2", "n3"} <= set(vec_ids)  # ticker maps to "nvidia"


def test_embeddings_are_unit_length():
    v = hashed_embed("Nvidia stock climbs")
    assert cosine(v, v) == pytest.approx(1.0)


def test_rrf_rewards_docs_in_both_lists():
    fused = rrf([["a", "b", "c"], ["b", "c", "d"]])
    assert fused[0][0] == "b"
    assert dict(fused)["b"] == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_handles_one_empty_list():
    assert [d for d, _ in rrf([[], ["x", "y"]])] == ["x", "y"]


def test_hybrid_top_hit_is_relevant(hs):
    assert hs.search("NVDA earnings")[0] in {"n1", "n2", "n3"}
    assert hs.search("Microsoft cloud forecast")[0] in {"n6", "n7"}
    assert hs.search("Tesla Autopilot recall")[0] == "n9"


def test_mmr_diversifies_near_duplicates():
    vecs = {"a": [1.0, 0.0], "b": [1.0, 0.0], "c": [0.6, 0.8]}
    picked = mmr([1.0, 0.0], ["a", "b", "c"], vecs, top_n=2, lam=0.4)
    assert picked == ["a", "c"]  # b is a duplicate of a, so c wins slot 2


def test_mmr_lambda_one_is_pure_relevance():
    vecs = {"a": [1.0, 0.0], "b": [1.0, 0.0], "c": [0.6, 0.8]}
    assert mmr([1.0, 0.0], ["a", "b", "c"], vecs, top_n=2, lam=1.0) == ["a", "b"]


def test_custom_embedder_is_pluggable():
    calls = []

    def fake(text):
        calls.append(text)
        return hashed_embed(text)

    HybridSearch({"x": "apple iphone"}, embed=fake).search("apple")
    assert "apple" in calls
