"""Cheap token counter. ~4 chars per token is the usual rule of thumb for English."""
import math


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))
