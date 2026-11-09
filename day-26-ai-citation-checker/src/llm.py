"""Optional LLM judge for gray-zone claims. FakeJudge keeps tests offline."""
import os


class FakeJudge:
    def __init__(self, answers: dict[str, bool] | None = None):
        self.answers = answers or {}

    def supported(self, claim: str, source: str) -> bool:
        return self.answers.get(claim, False)


class OllamaJudge:
    def __init__(self, model: str = os.getenv("OLLAMA_MODEL", "llama3.2")):
        self.model = model

    def supported(self, claim: str, source: str) -> bool:
        import requests
        prompt = (f"SOURCE:\n{source}\n\nCLAIM: {claim}\n\n"
                  "Is the CLAIM fully supported by the SOURCE? Answer only yes or no.")
        r = requests.post("http://localhost:11434/api/generate",
                          json={"model": self.model, "prompt": prompt, "stream": False}, timeout=60)
        return r.json()["response"].strip().lower().startswith("yes")


def judge_gray_zone(claims, sources, judge, low=0.3, high=0.6):
    """Ask the judge only when word-overlap is unsure (cheap first, LLM second)."""
    for c in claims:
        if c.verdict == "UNSUPPORTED" and low <= c.score < high and not c.missing_numbers:
            if any(judge.supported(c.text, sources[i]) for i in c.cites if i in sources):
                c.verdict = "SUPPORTED"
    return claims
