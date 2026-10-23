"""LLM backends. RuleLLM works offline; OpenAICompatLLM talks to Groq or Ollama."""
import json
import os
import re
import urllib.request

NAMES = {"apple": "AAPL", "microsoft": "MSFT", "tesla": "TSLA", "amazon": "AMZN", "nvidia": "NVDA"}
POS = ("jump", "rise", "beat", "soar", "gain")
NEG = ("slip", "fall", "miss", "drop", "weak", "cut")


class RuleLLM:
    """Pretend LLM: keyword rules -> JSON text. `bad_first` simulates a sloppy model."""

    def __init__(self, bad_first: bool = False):
        self.bad_first = bad_first
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        if self.bad_first and self.calls == 1:
            return "Sure! ticker is NVDA, looks positive"  # not JSON -> forces a retry
        text = prompt.rsplit("HEADLINE:", 1)[-1].strip()
        low = text.lower()
        m = re.search(r"\b([A-Z]{2,5})\b", text)
        ticker = m.group(1) if m else next((t for n, t in NAMES.items() if n in low), "UNK")
        sign = 1 if any(w in low for w in POS) else -1 if any(w in low for w in NEG) else 0
        pm = re.search(r"(\d+(?:\.\d+)?)%", text)
        pct = sign * float(pm.group(1)) if pm and sign else None
        etype = ("buyback" if "buyback" in low else "earnings" if "earning" in low or "revenue" in low
                 else "sales" if "sales" in low or "deliver" in low else "other")
        sent = {1: "positive", -1: "negative", 0: "neutral"}[sign]
        return json.dumps({"ticker": ticker, "sentiment": sent, "pct_move": pct, "event_type": etype})


class OpenAICompatLLM:
    """Groq (GROQ_API_KEY) or Ollama (OLLAMA_MODEL) via the OpenAI chat API shape."""

    def __init__(self):
        if os.getenv("GROQ_API_KEY"):
            self.url = "https://api.groq.com/openai/v1/chat/completions"
            self.model, self.key = "llama-3.1-8b-instant", os.environ["GROQ_API_KEY"]
        else:
            self.url = "http://localhost:11434/v1/chat/completions"
            self.model, self.key = os.environ["OLLAMA_MODEL"], "ollama"

    def complete(self, prompt: str) -> str:
        body = json.dumps({"model": self.model, "temperature": 0,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(self.url, body, {"Content-Type": "application/json",
                                                      "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["choices"][0]["message"]["content"]


def pick_llm():
    return OpenAICompatLLM() if os.getenv("GROQ_API_KEY") or os.getenv("OLLAMA_MODEL") else RuleLLM()
