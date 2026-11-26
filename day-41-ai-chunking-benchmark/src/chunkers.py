"""Three ways to cut documents into chunks for RAG."""
import re

def fixed(text: str, size: int = 200, overlap: int = 40) -> list[str]:
    """Fixed-size character windows. Each window starts size-overlap after the last."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("need size > 0 and 0 <= overlap < size")
    text = text.strip()
    step, out = size - overlap, []
    for start in range(0, len(text), step):
        piece = text[start:start + size].strip()
        if piece:
            out.append(piece)
        if start + size >= len(text):
            break
    return out

_SENT = re.compile(r"(?<=[.!?])\s+")

def sentences(text: str, max_chars: int = 300) -> list[str]:
    """Pack whole sentences into chunks up to max_chars. Never cuts a sentence
    unless one sentence alone is longer than max_chars."""
    out, cur = [], ""
    for s in (x.strip() for x in _SENT.split(text.strip())):
        if not s:
            continue
        if len(s) > max_chars:                    # giant sentence: hard cut it
            if cur:
                out.append(cur); cur = ""
            out.extend(fixed(s, max_chars, 0))
        elif not cur:
            cur = s
        elif len(cur) + 1 + len(s) <= max_chars:
            cur += " " + s
        else:
            out.append(cur); cur = s
    if cur:
        out.append(cur)
    return out

SEPARATORS = ["\n\n", "\n", ". ", " "]

def recursive(text: str, max_chars: int = 300, seps=SEPARATORS) -> list[str]:
    """Split on the biggest separator first (paragraph, line, sentence, word),
    only going smaller for pieces that are still too long. Then merge small
    neighbours back up to max_chars."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    if not seps:
        return fixed(text, max_chars, 0)
    sep, rest = seps[0], seps[1:]
    parts = [p for p in text.split(sep) if p.strip()]
    if len(parts) == 1:
        return recursive(text, max_chars, rest)
    out, cur = [], ""
    for p in parts:
        p = p.strip()
        if len(p) > max_chars:
            if cur:
                out.append(cur); cur = ""
            out.extend(recursive(p, max_chars, rest))
            continue
        joiner = "" if not cur else (" " if sep.strip() == "" else sep.rstrip() + " " if sep == ". " else sep)
        if cur and len(cur) + len(joiner) + len(p) <= max_chars:
            cur += joiner + p
        else:
            if cur:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return out
