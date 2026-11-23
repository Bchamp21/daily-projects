"""Judges compare two answers to one question and return 'A', 'B' or 'TIE'.

HeuristicJudge is offline and deterministic (for tests).
OllamaJudge calls a local model (OLLAMA_URL, default http://localhost:11434).
"""
import os
import re

RUBRIC = (
    "You are a strict grader. Question: {q}\n"
    "Reference facts: {ref}\n\nAnswer A:\n{a}\n\nAnswer B:\n{b}\n\n"
    "Which answer is more correct and complete, using only the reference facts? "
    "Reply with exactly one word: A, B or TIE."
)


def _tokens(text: str) -> set[str]:
    return {t.strip(".") for t in re.findall(r"[a-z0-9.%$]+", text.lower())} - {""}


class HeuristicJudge:
    """Scores each answer by how many reference facts it covers, minus a length penalty.

    position_bias > 0 simulates a biased judge that nudges whichever answer is shown first.
    """

    def __init__(self, position_bias: float = 0.0):
        self.position_bias = position_bias

    def score(self, answer: str, ref: str) -> float:
        facts = _tokens(ref)
        if not facts:
            return 0.0
        covered = len(facts & _tokens(answer)) / len(facts)
        rambling = max(0, len(answer.split()) - 60) * 0.005
        return covered - rambling

    def compare(self, q: str, a: str, b: str, ref: str) -> str:
        sa = self.score(a, ref) + self.position_bias
        sb = self.score(b, ref)
        if abs(sa - sb) < 0.05:
            return "TIE"
        return "A" if sa > sb else "B"


class OllamaJudge:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate"

    def compare(self, q: str, a: str, b: str, ref: str) -> str:
        import requests  # optional dependency

        prompt = RUBRIC.format(q=q, ref=ref, a=a, b=b)
        r = requests.post(self.url, json={"model": self.model, "prompt": prompt,
                                          "stream": False, "options": {"temperature": 0}}, timeout=60)
        return parse_verdict(r.json().get("response", ""))


def parse_verdict(text: str) -> str:
    """Pull A / B / TIE out of a chatty model reply. Unknown -> TIE (never guess a winner)."""
    m = re.search(r"\b(TIE|A|B)\b", text.strip().upper())
    return m.group(1) if m else "TIE"

