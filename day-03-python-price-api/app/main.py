"""FastAPI service: validate -> store -> query -> analyze."""
import os

from fastapi import Depends, FastAPI, HTTPException, Query

from . import db
from .analytics import simple_moving_average
from .models import PriceIn, PriceOut, SMAOut

app = FastAPI(title="Stock Price API", version="0.1.0")
_conn = None


def get_conn():
    """Dependency: tests override this with an in-memory DB."""
    global _conn
    if _conn is None:
        _conn = db.connect(os.getenv("PRICES_DB", "prices.db"))
    return _conn


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/prices", response_model=PriceOut, status_code=201)
def add_price(price: PriceIn, conn=Depends(get_conn)):
    row = price.model_dump()
    row["trade_date"] = price.trade_date.isoformat()
    db.upsert(conn, row)
    return price


@app.get("/prices/{ticker}", response_model=list[PriceOut])
def list_prices(ticker: str, conn=Depends(get_conn)):
    rows = db.get_prices(conn, ticker)
    if not rows:
        raise HTTPException(404, f"no prices for {ticker.upper()}")
    return rows


@app.get("/prices/{ticker}/sma", response_model=SMAOut)
def sma(ticker: str, window: int = Query(3, ge=1, le=200), conn=Depends(get_conn)):
    rows = db.get_prices(conn, ticker)
    if not rows:
        raise HTTPException(404, f"no prices for {ticker.upper()}")
    values = simple_moving_average([r["close"] for r in rows], window)
    points = [{"trade_date": r["trade_date"], "close": r["close"], "sma": v}
              for r, v in zip(rows, values)]
    return SMAOut(ticker=ticker.upper(), window=window, points=points)
