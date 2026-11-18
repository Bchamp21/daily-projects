"""Safe LLM call: redact -> check leaks -> LLM -> restore."""
import os
from vault import Vault


class LeakError(RuntimeError):
    pass


class FakeLLM:
    """Offline stand-in: echoes the tokens it was given, like a real summarizer would."""

    def __init__(self):
        self.seen: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.seen.append(prompt)
        import re
        toks = re.findall(r"<[A-Z]+_\d+>", prompt)
        return "Summary: follow up with " + ", ".join(dict.fromkeys(toks)) + "."


class OllamaLLM:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate"

    def __call__(self, prompt: str) -> str:
        import requests
        r = requests.post(self.url, json={"model": self.model, "prompt": prompt, "stream": False}, timeout=120)
        r.raise_for_status()
        return r.json()["response"]


INSTRUCTION = "Keep placeholders like <EMAIL_1> exactly as written. "


def safe_call(llm, text: str, vault: Vault | None = None) -> dict:
    vault = vault or Vault()
    redacted = vault.redact(text)
    if vault.leaks(redacted):
        raise LeakError("PII still present after redaction")
    raw = llm(INSTRUCTION + redacted)
    return {
        "redacted": redacted,
        "llm_raw": raw,
        "answer": vault.restore(raw),
        "unknown_tokens": vault.unknown_tokens(raw),
        "counts": dict(vault.counts),
    }
