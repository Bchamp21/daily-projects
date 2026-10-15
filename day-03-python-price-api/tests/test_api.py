import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app, get_conn


@pytest.fixture()
def client():
    conn = db.connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def row(d, price, **kw):
    base = {"ticker": "aapl", "trade_date": d, "open": price, "high": price + 2,
            "low": price - 2, "close": price, "volume": 1000}
    base.update(kw)
    return base


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_post_and_get_uppercases_ticker(client):
    r = client.post("/prices", json=row("2026-10-01", 100))
    assert r.status_code == 201 and r.json()["ticker"] == "AAPL"
    got = client.get("/prices/aapl").json()
    assert len(got) == 1 and got[0]["close"] == 100


def test_upsert_same_day_replaces(client):
    client.post("/prices", json=row("2026-10-01", 100))
    client.post("/prices", json=row("2026-10-01", 105))
    got = client.get("/prices/AAPL").json()
    assert len(got) == 1 and got[0]["close"] == 105


@pytest.mark.parametrize("bad", [
    {"close": -5},                     # negative price
    {"ticker": "AP1"},                 # digits in ticker
    {"high": 90, "low": 95},           # high < low
    {"volume": -1},                    # negative volume
])
def test_validation_rejects_bad_rows(client, bad):
    assert client.post("/prices", json=row("2026-10-01", 100, **bad)).status_code == 422


def test_sma_endpoint(client):
    for d, c in [("2026-10-01", 10), ("2026-10-02", 20), ("2026-10-03", 30)]:
        client.post("/prices", json=row(d, c))
    body = client.get("/prices/AAPL/sma?window=2").json()
    assert [p["sma"] for p in body["points"]] == [None, 15.0, 25.0]


def test_missing_ticker_404(client):
    assert client.get("/prices/MSFT").status_code == 404
