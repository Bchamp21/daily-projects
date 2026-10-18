import json
from pathlib import Path

from pricecheck.cli import main
from pricecheck.validator import validate_file

SAMPLE = Path(__file__).parent.parent / "data" / "prices_sample.csv"


def test_sample_file_counts():
    r = validate_file(SAMPLE)
    assert r.total == 8
    assert len(r.good) == 3          # AAPL, MSFT, NVDA
    assert r.duplicates == 1         # second AAPL row
    assert len(r.bad) == 4           # TSLA, GOOG, AMZN, JNJ
    assert [b["line"] for b in r.bad] == [6, 7, 8, 9]


def test_cli_writes_clean_csv_and_report(tmp_path, capsys):
    out, rep = tmp_path / "clean.csv", tmp_path / "report.json"
    code = main([str(SAMPLE), "--out", str(out), "--report", str(rep)])
    assert code == 0
    assert out.read_text().count("\n") == 4  # header + 3 rows
    assert json.loads(rep.read_text())["pass_rate_pct"] == 37.5
    assert "good=3" in capsys.readouterr().out


def test_cli_fails_pipeline_below_threshold():
    assert main([str(SAMPLE), "--min-pass", "90"]) == 1


def test_cli_missing_file():
    assert main(["nope.csv"]) == 2
