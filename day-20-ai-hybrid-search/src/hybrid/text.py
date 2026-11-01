import re

STOP = {"the", "a", "an", "on", "in", "of", "as", "and", "but", "to", "over", "after", "from", "into", "up"}
SYNONYMS = {  # tiny alias map so the vector side "knows" tickers = company names
    "nvda": "nvidia", "aapl": "apple", "msft": "microsoft", "tsla": "tesla",
    "gpu": "chip", "chips": "chip", "results": "earnings", "estimates": "forecast",
    "forecasts": "forecast", "shares": "stock", "stocks": "stock", "rise": "climb",
    "climbs": "climb", "jumps": "climb", "rally": "climb",
}


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def normalize(tokens: list[str]) -> list[str]:
    return [SYNONYMS.get(t, t) for t in tokens]
