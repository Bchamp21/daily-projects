"""FakeLLM obeys any instruction it sees (worst case), so tests prove the guard works.
OllamaLLM is optional for a real local model."""


class FakeLLM:
    def generate(self, prompt: str) -> str:
        p = "\n".join(prompt.splitlines()[1:]).lower()  # docs + question only
        out = []
        if "reveal" in p or "system prompt" in p:
            out.append(prompt.splitlines()[0])         # leaks the system line
        if "send_email" in p:
            out.append("TOOL: send_email(to='attacker@x.com')")
        if "aapl" in p:
            out.append("TOOL: get_price('AAPL')")
            out.append("AAPL rose 3% after strong iPhone sales.")
        return "\n".join(out) or "No relevant news found."


class OllamaLLM:
    def __init__(self, model: str = "llama3.2"):
        self.model = model

    def generate(self, prompt: str) -> str:
        import requests
        r = requests.post("http://localhost:11434/api/generate",
                          json={"model": self.model, "prompt": prompt, "stream": False}, timeout=60)
        r.raise_for_status()
        return r.json()["response"]
