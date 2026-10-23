"""Prompt -> LLM -> parse JSON -> validate -> retry with the error if it fails."""
import json
import re
from pydantic import ValidationError
from .schema import NewsEvent

PROMPT = """Extract one stock news event as JSON only, no prose.
Keys: ticker (1-5 letters), sentiment (positive|negative|neutral),
pct_move (number or null, negative if the stock fell), event_type (earnings|buyback|sales|guidance|other).
{feedback}HEADLINE: {headline}"""


def parse_json(text: str) -> dict:
    """Models often wrap JSON in ```json fences or chatter; grab the first {...} block."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in model output")
    return json.loads(m.group(0))


def extract(headline: str, llm, max_tries: int = 3) -> NewsEvent:
    feedback = ""
    for attempt in range(1, max_tries + 1):
        raw = llm.complete(PROMPT.format(feedback=feedback, headline=headline))
        try:
            return NewsEvent(**parse_json(raw))
        except (ValueError, ValidationError) as e:  # JSONDecodeError is a ValueError
            feedback = f"Your last answer was invalid: {str(e)[:200]}. Fix it.\n"
    raise RuntimeError(f"gave up after {max_tries} tries: {headline!r}")
