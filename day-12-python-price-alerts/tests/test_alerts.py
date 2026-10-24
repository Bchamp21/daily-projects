import json
from pathlib import Path

import pytest

from pricealerts import build_rule, evaluate, load_prices, load_rules
from pricealerts.__main__ import main
from pricealerts.rules import RuleConfigError

SAMPLE = Path(__file__).parent.parent / "sample"


@pytest.mark.parametrize("cfg, closes, fires", [
    ({"type": "above", "ticker": "x", "price": 10}, [9, 11], True),
    ({"type": "above", "ticker": "x", "price": 10}, [11, 10], False),
    ({"type": "below", "ticker": "x", "price": 10}, [11, 9.5], True),
    ({"type": "pct_change", "ticker": "x", "pct": 5}, [100, 94], True),
    ({"type": "pct_change", "ticker": "x", "pct": 5}, [100, 104], False),
    ({"type": "pct_change", "ticker": "x", "pct": 5}, [100], False),
    ({"type": "sma_cross", "ticker": "x", "window": 3}, [10, 10, 10, 9, 12], True),
    ({"type": "sma_cross", "ticker": "x", "window": 3}, [10, 11, 12, 13, 14], False),
    ({"type": "sma_cross", "ticker": "x", "window": 3}, [10, 11], False),
])
def test_rules(cfg, closes, fires):
    rule = build_rule(cfg)
    assert rule.ticker == "X"
    assert (rule.check(closes) is not None) is fires


@pytest.mark.parametrize("cfg", [
    {"type": "nope", "ticker": "X"},
    {"type": "above"},
    {"type": "above", "ticker": "X", "colour": "red"},
])
def test_bad_config(cfg):
    with pytest.raises(RuleConfigError):
        build_rule(cfg)


def test_load_prices_sorts_and_skips_bad_rows(tmp_path, caplog):
    f = tmp_path / "p.csv"
    f.write_text("ticker,date,close\naapl,2026-01-02,2\nAAPL,2026-01-01,1\nAAPL,2026-01-03,oops\n")
    assert load_prices(f) == {"AAPL": [1.0, 2.0]}
    assert "skipping bad row 4" in caplog.text


def test_sample_end_to_end():
    alerts = evaluate(load_rules(SAMPLE / "rules.json"), load_prices(SAMPLE / "prices.csv"))
    kinds = sorted((a.ticker, a.rule) for a in alerts)
    assert kinds == [("AAPL", "above"), ("AAPL", "sma_cross"), ("MSFT", "below"), ("MSFT", "pct_change")]


def test_cli_json_and_exit_code(capsys):
    code = main(["--prices", str(SAMPLE / "prices.csv"), "--rules", str(SAMPLE / "rules.json"), "--json"])
    assert code == 1
    assert len(json.loads(capsys.readouterr().out)) == 4


def test_cli_config_error(tmp_path, capsys):
    bad = tmp_path / "r.json"
    bad.write_text('{"rules": [{"type": "moon", "ticker": "X"}]}')
    assert main(["--prices", str(SAMPLE / "prices.csv"), "--rules", str(bad)]) == 2
    assert "unknown rule type" in capsys.readouterr().err
