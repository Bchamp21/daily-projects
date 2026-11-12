import os


class FakeLLM:
    """Counts calls so tests can prove the cache saved them."""

    def __init__(self):
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        return f"answer#{self.calls} for: {prompt}"


class OllamaLLM:  # pragma: no cover
    def __init__(self, model: str = "llama3.2"):
        import requests
        self.requests, self.model = requests, model
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        r = self.requests.post(f"{self.url}/api/generate",
                               json={"model": self.model, "prompt": prompt, "stream": False},
                               timeout=120)
        r.raise_for_status()
        return r.json()["response"]
