"""LLM providers. Offline fakes for tests; real ones read keys from env vars only."""
import os


class ProviderError(Exception):
    pass


class Provider:
    name = "base"
    cost_per_1k_tokens = 0.0

    def complete(self, prompt: str) -> str:
        raise NotImplementedError


class EchoProvider(Provider):
    """Deterministic offline 'LLM' so everything runs without keys."""

    def __init__(self, name="echo", cost_per_1k_tokens=0.0):
        self.name = name
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        return f"[{self.name}] answer to: {prompt.strip()}"


class FlakyProvider(EchoProvider):
    """Fails the first `fail_times` calls, to test fallback."""

    def __init__(self, fail_times=1, **kw):
        super().__init__(**kw)
        self.fail_times = fail_times

    def complete(self, prompt: str) -> str:
        if self.fail_times > 0:
            self.fail_times -= 1
            self.calls += 1
            raise ProviderError(f"{self.name} timed out")
        return super().complete(prompt)


class GroqProvider(Provider):
    """Real provider (optional). Needs GROQ_API_KEY in the environment."""
    name = "groq"
    cost_per_1k_tokens = 0.0  # free tier

    def __init__(self, model="llama-3.1-8b-instant"):
        self.model = model

    def complete(self, prompt: str) -> str:
        import requests
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise ProviderError("GROQ_API_KEY not set")
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
                timeout=20,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:  # network, HTTP, parsing
            raise ProviderError(str(e)) from e


class OllamaProvider(Provider):
    """Real local provider (optional). Needs `ollama serve` running."""
    name = "ollama"

    def __init__(self, model="llama3.2"):
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def complete(self, prompt: str) -> str:
        import requests
        try:
            r = requests.post(f"{self.host}/api/generate",
                              json={"model": self.model, "prompt": prompt, "stream": False}, timeout=60)
            r.raise_for_status()
            return r.json()["response"]
        except Exception as e:
            raise ProviderError(str(e)) from e
