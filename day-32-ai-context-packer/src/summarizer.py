"""Summarizers turn old chat turns into one short memory line."""
import os


class FakeSummarizer:
    """Offline: keeps the first sentence of each turn, counts calls."""

    def __init__(self, max_chars: int = 240):
        self.calls = 0
        self.max_chars = max_chars

    def __call__(self, turns):
        self.calls += 1
        bits = []
        for t in turns:
            first = t["content"].split(". ")[0].strip().rstrip(".")
            bits.append(f"{t['role']}: {first}")
        text = "; ".join(bits)
        return text[: self.max_chars]


class OllamaSummarizer:
    """Real summaries with a local model (needs `requests` and `ollama pull llama3.2`)."""

    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate"

    def __call__(self, turns):
        import requests

        convo = "\n".join(f"{t['role']}: {t['content']}" for t in turns)
        prompt = ("Summarize this chat in 2 short sentences. Keep tickers, numbers and "
                  "user preferences.\n\n" + convo)
        r = requests.post(self.url, json={"model": self.model, "prompt": prompt, "stream": False}, timeout=60)
        r.raise_for_status()
        return r.json()["response"].strip()
