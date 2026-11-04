"""Layer 1: score retrieved text for injection attempts (cheap heuristics)."""
import re
import unicodedata

PATTERNS = {
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)": 0.6,
    r"disregard (the )?(system|previous) (prompt|instructions)": 0.6,
    r"you are now\b": 0.4,
    r"(reveal|print|show) (the |your )?(system prompt|instructions|secret|api key)": 0.6,
    r"call (the )?(tool|function) ": 0.3,
    r"send (an )?email|transfer \$?\d": 0.4,
    r"</?(system|assistant)>": 0.5,
}
ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")


def normalize(text: str) -> str:
    """Strip zero-width chars and fold unicode tricks before matching."""
    text = ZERO_WIDTH.sub("", text)
    return unicodedata.normalize("NFKC", text).lower()


def injection_score(text: str) -> tuple[float, list[str]]:
    t = normalize(text)
    hits = [p for p in PATTERNS if re.search(p, t)]
    score = min(1.0, sum(PATTERNS[p] for p in hits))
    return score, hits
