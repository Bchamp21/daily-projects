"""Reversible redaction: PII -> <EMAIL_1>, and back again after the LLM answers."""
import re
from detectors import find_pii

TOKEN = re.compile(r"<([A-Z]+)_(\d+)>")


class Vault:
    """Lives only in your process. The LLM never sees the real values."""

    def __init__(self, allow: set[str] | None = None):
        self.allow = allow or set()
        self.to_token: dict[tuple[str, str], str] = {}
        self.to_value: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    def _token_for(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self.to_token:  # same value -> same token, so the LLM can reason about it
            self.counts[kind] = self.counts.get(kind, 0) + 1
            tok = f"<{kind}_{self.counts[kind]}>"
            self.to_token[key] = tok
            self.to_value[tok] = value
        return self.to_token[key]

    def redact(self, text: str) -> str:
        out, last = [], 0
        for sp in find_pii(text, self.allow):
            out.append(text[last:sp.start])
            out.append(self._token_for(sp.kind, sp.text))
            last = sp.end
        out.append(text[last:])
        return "".join(out)

    def restore(self, text: str) -> str:
        """Swap tokens back. Unknown tokens (LLM made one up) are left as-is and reported."""
        return TOKEN.sub(lambda m: self.to_value.get(m.group(0), m.group(0)), text)

    def unknown_tokens(self, text: str) -> list[str]:
        return [m.group(0) for m in TOKEN.finditer(text) if m.group(0) not in self.to_value]

    def leaks(self, text: str) -> list[str]:
        """Real values that still appear in text meant for the LLM. Should be []."""
        return [v for v in self.to_value.values() if v in text]
