from pathlib import Path

from kpi.cli import main
from kpi.report import load_rows, monthly_kpis, safe_pct, to_markdown

DATA = Path(__file__).parent.parent / "data" / "trades.csv"


def test_bad_rows_rejected_not_crashing():
    rows, bad = load_rows(DATA)
    assert len(rows) == 7 and len(bad) == 2
    assert "line 7" in bad[0] and "line 10" in bad[1]


def test_monthly_revenue_and_running_total():
    k = monthly_kpis(load_rows(DATA)[0])
    assert [x.month for x in k] == ["2026-09", "2026-10", "2026-11"]
    assert k[0].revenue == 2205 + 2050 + 900      # 5155
    assert k[1].revenue == 3322 + 2368            # 5690
    assert k[2].revenue == 3500 + 2520            # 6020
    assert k[2].running_total == 5155 + 5690 + 6020


def test_mom_and_top_ticker():
    k = monthly_kpis(load_rows(DATA)[0])
    assert k[0].mom_pct is None
    assert k[1].mom_pct == 10.4                   # (5690-5155)/5155
    assert k[0].top_ticker == "AAPL" and k[2].top_ticker == "NVDA"


def test_safe_pct_zero_base():
    assert safe_pct(100, 0) is None and safe_pct(100, None) is None
    assert safe_pct(50, 100) == -50.0


def test_markdown_and_cli(tmp_path, capsys):
    md = to_markdown(monthly_kpis(load_rows(DATA)[0]), ["x"])
    assert "| 2026-10 | 5,690.00 | 2 | +10.4% |" in md and "Rejected rows (1)" in md
    out = tmp_path / "r.md"
    assert main([str(DATA), "--out", str(out)]) == 1
    assert "NVDA" in out.read_text()
