"""LLM backends. Each returns the next step as a dict:
  {"tool": name, "args": {...}}   or   {"final": "answer text"}
"""
import json
import os
import re
import urllib.request

from .tools import PRICES, TOOLS

SYSTEM = (
    "You are a stock assistant. Use tools to get numbers; never guess.\n"
    "Tools:\n" + "\n".join(f"- {t['desc']}" for t in TOOLS.values()) +
    '\nReply with ONLY JSON: {"tool": "...", "args": {...}} to call a tool, '
    'or {"final": "..."} when done.'
)


class RuleLLM:
    """Offline stand-in for an LLM: keyword routing. Free, deterministic."""

    def next_step(self, messages: list[dict]) -> dict:
        question = messages[1]["content"].lower()
        results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        symbols = [s for s in PRICES if s.lower() in question]
        if not symbols:
            return {"final": f"Ask about one of: {', '.join(sorted(PRICES))}."}
        if "average" in question or "sma" in question:
            tool, extra = "moving_average", {"window": int((re.findall(r"\d+", question) or [3])[0])}
        elif "return" in question or "best" in question or "compare" in question:
            tool, extra = "pct_return", {}
        else:
            tool, extra = "latest_price", {}
        done = {r.get("symbol") for r in results}
        for s in symbols:
            if s not in done:
                return {"tool": tool, "args": {"symbol": s, **extra}}
        return {"final": summarize(tool, results)}


def summarize(tool: str, results: list[dict]) -> str:
    if any("error" in r for r in results):
        return "Tool error: " + "; ".join(r["error"] for r in results if "error" in r)
    if tool == "pct_return":
        best = max(results, key=lambda r: r["pct"])
        parts = ", ".join(f"{r['symbol']} {r['pct']:+.2f}%" for r in results)
        return f"Returns: {parts}. Best: {best['symbol']}."
    if tool == "moving_average":
        return ", ".join(f"{r['symbol']} {r['window']}-day SMA {r['sma']}" for r in results)
    return ", ".join(f"{r['symbol']} closed at {r['close']} on {r['date']}" for r in results)


class OpenAICompatLLM:
    """Groq or Ollama via the OpenAI-style /chat/completions API (stdlib only).
    Groq:   GROQ_API_KEY set  -> https://api.groq.com/openai/v1
    Ollama: OLLAMA_MODEL set  -> http://localhost:11434/v1 (no key)
    """

    def __init__(self):
        if os.getenv("GROQ_API_KEY"):
            self.url = "https://api.groq.com/openai/v1/chat/completions"
            self.key = os.environ["GROQ_API_KEY"]
            self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        else:
            self.url = "http://localhost:11434/v1/chat/completions"
            self.key = "ollama"
            self.model = os.getenv("OLLAMA_MODEL", "llama3.2")

    def next_step(self, messages: list[dict]) -> dict:
        # Tool results go back as plain user turns so any chat model understands them.
        msgs = [{"role": "user" if m["role"] == "tool" else m["role"],
                 "content": ("TOOL RESULT: " if m["role"] == "tool" else "") + m["content"]}
                for m in messages]
        body = json.dumps({"model": self.model, "messages": msgs, "temperature": 0}).encode()
        req = urllib.request.Request(self.url, body, {
            "Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = json.load(r)["choices"][0]["message"]["content"]
        return parse_step(text)


def parse_step(text: str) -> dict:
    """Pull the first JSON object out of model text; fall back to a final answer."""
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            step = json.loads(m.group(0))
            if "tool" in step or "final" in step:
                step.setdefault("args", {}) if "tool" in step else None
                return step
        except json.JSONDecodeError:
            pass
    return {"final": text.strip()}


def pick_llm():
    if os.getenv("GROQ_API_KEY") or os.getenv("OLLAMA_MODEL"):
        return OpenAICompatLLM()
    return RuleLLM()
