import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import genie_check as g  # noqa: E402


@pytest.fixture
def cfg():
    return g.load()


@pytest.fixture(scope="module")
def con():
    return g.local_gold()


def test_shipped_config_is_valid(cfg):
    assert g.validate(cfg) == []


def test_two_part_name_rejected(cfg):
    bad = copy.deepcopy(cfg)
    bad["tables"].append("gold.prices")
    assert any("catalog.schema.table" in e for e in g.validate(bad))


@pytest.mark.parametrize("sql,needle", [
    ("DELETE FROM market.gold.gold_ticker_summary", "SELECT"),
    ("SELECT 1; DROP TABLE market.gold.gold_ticker_summary", "write/DDL"),
    ("SELECT * FROM market.silver.prices", "unknown table"),
])
def test_unsafe_sql_caught(sql, needle):
    allowed = {"market.gold.gold_ticker_summary"}
    assert any(needle in e for e in g.check_sql(sql, allowed))


def test_duplicate_sample_question(cfg):
    bad = copy.deepcopy(cfg)
    bad["sample_queries"].append(dict(bad["sample_queries"][0]))
    assert any("duplicate" in e for e in g.validate(bad))


def test_comments_sql_escapes_quotes(cfg):
    c = copy.deepcopy(cfg)
    c["column_docs"]["market.gold.gold_ticker_summary"]["ticker"] = "Bhuvan's symbol"
    assert "Bhuvan''s symbol" in g.comments_sql(c)


def test_drawdown_never_positive(con):
    assert con.execute("SELECT MAX(drawdown) FROM gold_price_metrics").fetchone()[0] <= 0


def test_summary_one_row_per_ticker(con):
    rows = con.execute("SELECT ticker, trading_days FROM gold_ticker_summary ORDER BY ticker").fetchall()
    assert rows == [("AAPL", 5), ("MSFT", 5)]


def test_to_local_strips_catalog():
    assert g.to_local("SELECT * FROM market.gold.t") == "SELECT * FROM t"


def test_bench_passes_different_sql_same_answer(cfg, con):
    answers = json.loads((ROOT / "answers.example.json").read_text())
    rep = g.bench(cfg, answers, con)
    assert rep["score"] == 1.0


def test_bench_flags_wrong_missing_unsafe(cfg, con):
    qs = [b["question"] for b in cfg["benchmarks"]]
    answers = {
        qs[0]: "SELECT ticker FROM market.gold.gold_ticker_summary ORDER BY period_return ASC LIMIT 1",
        qs[1]: "DELETE FROM market.gold.gold_ticker_summary",
    }
    status = {r["question"]: r["status"] for r in g.bench(cfg, answers, con)["results"]}
    assert status == {qs[0]: "wrong", qs[1]: "unsafe", qs[2]: "missing"}


def test_cli_exit_codes(tmp_path):
    assert g.main(["validate"]) == 0
    bad = tmp_path / "a.json"
    bad.write_text("{}")
    assert g.main(["bench", "--answers", str(bad)]) == 1
