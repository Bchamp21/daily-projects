"""LLMs that turn a question + schema into SQL.

RuleLLM is offline (for tests). OllamaLLM / GroqLLM are optional real models.
Keys are read only from env vars (GROQ_API_KEY); nothing is committed.
"""
import os
import re


class RuleLLM:
    """Pattern-matching stand-in for a real model. Makes one deliberate typo
    on 'average' questions so we can test the self-correction loop."""

    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        q = prompt.split("QUESTION:")[-1].lower()
        fixing = "ERROR:" in prompt
        t = re.search(r"\b(aapl|msft|nvda)\b", q)
        ticker = t.group(1).upper() if t else None
        if "drop" in q or "delete" in q:
            return "DROP TABLE prices"
        if "average" in q and ticker:
            col = "close" if fixing else "closing_price"  # typo first time
            return f"SELECT AVG({col}) AS avg_close FROM prices WHERE ticker = '{ticker}'"
        if "highest volume" in q:
            return "SELECT ticker, trade_date, volume FROM prices ORDER BY volume DESC LIMIT 1"
        if "latest" in q and ticker:
            return (f"SELECT trade_date, close FROM prices WHERE ticker = '{ticker}' "
                    "ORDER BY trade_date DESC LIMIT 1")
        return "SELECT ticker, COUNT(*) AS days FROM prices GROUP BY ticker"


class OllamaLLM:
    def __init__(self, model: str = "llama3.2"):
        self.model = model

    def generate(self, prompt: str) -> str:
        import requests
        r = requests.post("http://localhost:11434/api/generate",
                          json={"model": self.model, "prompt": prompt, "stream": False}, timeout=60)
        r.raise_for_status()
        return r.json()["response"]


class GroqLLM:
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.model = model
        self.key = os.environ["GROQ_API_KEY"]

    def generate(self, prompt: str) -> str:
        import requests
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers={"Authorization": f"Bearer {self.key}"},
                          json={"model": self.model, "temperature": 0,
                                "messages": [{"role": "user", "content": prompt}]}, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def extract_sql(text: str) -> str:
    """Pull SQL out of a ```sql fenced block if the model added one."""
    m = re.search(r"```(?:sql)?\s*(.+?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip()
