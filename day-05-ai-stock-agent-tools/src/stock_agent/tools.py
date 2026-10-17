"""Tools the agent can call. Plain Python functions + a registry."""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "prices.csv"


def load_prices(path: Path = DATA) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            out.setdefault(row["symbol"].upper(), []).append((row["date"], float(row["close"])))
    for rows in out.values():
        rows.sort()
    return out


PRICES = load_prices()


def _series(symbol: str) -> list[tuple[str, float]]:
    s = symbol.upper()
    if s not in PRICES:
        raise ValueError(f"unknown symbol {s}; known: {sorted(PRICES)}")
    return PRICES[s]


def latest_price(symbol: str) -> dict:
    date, close = _series(symbol)[-1]
    return {"symbol": symbol.upper(), "date": date, "close": close}


def moving_average(symbol: str, window: int = 3) -> dict:
    closes = [c for _, c in _series(symbol)]
    window = int(window)
    if not 1 <= window <= len(closes):
        raise ValueError(f"window must be 1..{len(closes)}")
    return {"symbol": symbol.upper(), "window": window,
            "sma": round(sum(closes[-window:]) / window, 2)}


def pct_return(symbol: str) -> dict:
    s = _series(symbol)
    first, last = s[0][1], s[-1][1]
    return {"symbol": symbol.upper(), "from": s[0][0], "to": s[-1][0],
            "pct": round((last - first) / first * 100, 2)}


TOOLS = {
    "latest_price": {"fn": latest_price, "desc": "latest_price(symbol) -> last close"},
    "moving_average": {"fn": moving_average, "desc": "moving_average(symbol, window=3) -> SMA"},
    "pct_return": {"fn": pct_return, "desc": "pct_return(symbol) -> % change over the data"},
}


def call_tool(name: str, args: dict) -> dict:
    if name not in TOOLS:
        return {"error": f"unknown tool {name}"}
    try:
        return TOOLS[name]["fn"](**args)
    except (ValueError, TypeError) as e:
        return {"error": str(e)}
