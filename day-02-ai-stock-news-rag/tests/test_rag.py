"""Offline tests for Day 2 stock-news RAG."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stock_rag.answer import answer_question, extractive_answer
from stock_rag.corpus import load_corpus
from stock_rag.embedder import TfidfEmbedder, cosine_similarity, tokenize
from stock_rag.retriever import NewsRetriever


def test_corpus_loads():
    docs = load_corpus()
    assert len(docs) >= 8
    tickers = {d["ticker"] for d in docs}
    assert {"AAPL", "MSFT", "NVDA"} <= tickers


def test_tokenize_and_tfidf():
    assert "nvda" in tokenize("Why is NVDA mentioned?")
    emb = TfidfEmbedder().fit(["apple earnings grow", "nvidia gpu demand"])
    a = emb.transform("apple earnings")
    b = emb.transform("nvidia gpu")
    assert cosine_similarity(a, a) == pytest.approx(1.0, abs=1e-6)
    assert cosine_similarity(a, b) < cosine_similarity(a, emb.transform("apple"))


def test_retrieval_returns_relevant_ticker():
    ret = NewsRetriever()
    hits = ret.search("Why is NVDA mentioned in AI earnings?", k=3)
    assert hits
    assert any(h["ticker"] == "NVDA" for h in hits)
    assert hits[0]["score"] >= hits[-1]["score"]


def test_retrieval_aapl_query():
    hits = NewsRetriever().search("Apple MacBook AI features", k=2)
    assert hits
    assert hits[0]["ticker"] == "AAPL"


def test_extractive_answer_contains_snippet():
    ret = NewsRetriever()
    hits = ret.search("NVIDIA Blackwell GPUs hyperscalers", k=2)
    result = extractive_answer("NVIDIA Blackwell", hits)
    assert result["mode"] == "extractive"
    assert hits[0]["headline"] in result["answer"]
    assert result["citations"]


def test_empty_query_handled():
    result = answer_question("")
    assert "non-empty" in result["answer"].lower() or "enter" in result["answer"].lower()
    assert result["citations"] == []
    assert NewsRetriever().search("   ", k=3) == []


def test_answer_question_offline():
    result = answer_question("Microsoft Azure AI growth", k=2)
    assert result["mode"] == "extractive"
    assert "MSFT" in result["answer"] or any(c["ticker"] == "MSFT" for c in result["citations"])
