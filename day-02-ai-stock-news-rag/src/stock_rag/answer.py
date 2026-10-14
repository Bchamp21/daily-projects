"""Extractive answers + optional LLM polish (Gemini/Groq) when keys exist."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from stock_rag.retriever import NewsRetriever


def _synthesize_summary(hits: list[dict[str, Any]]) -> str:
    tickers = sorted({h["ticker"] for h in hits})
    bits = []
    for h in hits:
        bits.append(f"[{h['ticker']} {h['date']}] {h['headline']}")
    headline_block = "; ".join(bits)
    return (
        f"Based on {len(hits)} headline(s) about {', '.join(tickers)}: "
        f"{headline_block}."
    )


def extractive_answer(query: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Offline answer: quote best headlines + short synthesized summary."""
    if not hits:
        return {
            "mode": "extractive",
            "query": query,
            "answer": "No matching headlines found. Try a ticker (AAPL, MSFT, NVDA) or a topic.",
            "citations": [],
        }
    quotes = [
        f"- ({h['ticker']}, {h['date']}, score={h['score']}) {h['headline']} — {h['text'][:160]}..."
        if len(h["text"]) > 160
        else f"- ({h['ticker']}, {h['date']}, score={h['score']}) {h['headline']} — {h['text']}"
        for h in hits
    ]
    summary = _synthesize_summary(hits)
    body = summary + "\n\nTop matches:\n" + "\n".join(quotes)
    return {
        "mode": "extractive",
        "query": query,
        "answer": body,
        "citations": [
            {"id": h["id"], "ticker": h["ticker"], "headline": h["headline"], "score": h["score"]}
            for h in hits
        ],
    }


def _context_block(hits: list[dict[str, Any]]) -> str:
    parts = []
    for h in hits:
        parts.append(
            f"[{h['id']}|{h['ticker']}|{h['date']}] {h['headline']}\n{h['text']}"
        )
    return "\n\n".join(parts)


def _polish_with_groq(query: str, hits: list[dict[str, Any]], api_key: str) -> str | None:
    context = _context_block(hits)
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You answer questions about stock news using ONLY the provided "
                    "headlines. Cite tickers. Be concise (3-5 sentences)."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nHeadlines:\n{context}",
            },
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, TimeoutError):
        return None


def _polish_with_gemini(query: str, hits: list[dict[str, Any]], api_key: str) -> str | None:
    context = _context_block(hits)
    prompt = (
        "Answer using ONLY these stock headlines. Cite tickers. Be concise.\n\n"
        f"Question: {query}\n\nHeadlines:\n{context}"
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, TimeoutError):
        return None


def answer_question(
    query: str,
    retriever: NewsRetriever | None = None,
    k: int = 3,
) -> dict[str, Any]:
    """Retrieve top-k and answer extractively; polish with LLM if env key set."""
    q = (query or "").strip()
    if not q:
        return {
            "mode": "extractive",
            "query": query,
            "answer": "Please enter a non-empty question.",
            "citations": [],
        }
    ret = retriever or NewsRetriever()
    hits = ret.search(q, k=k)
    base = extractive_answer(q, hits)
    if not hits:
        return base

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    polished: str | None = None
    provider = None
    if groq_key:
        polished = _polish_with_groq(q, hits, groq_key)
        provider = "groq"
    elif gemini_key:
        polished = _polish_with_gemini(q, hits, gemini_key)
        provider = "gemini"

    if polished:
        return {
            "mode": f"llm:{provider}",
            "query": q,
            "answer": polished,
            "citations": base["citations"],
            "extractive_fallback": base["answer"],
        }
    return base
