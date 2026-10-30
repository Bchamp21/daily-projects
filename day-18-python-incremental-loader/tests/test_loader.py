import sqlite3
from pathlib import Path

from incload.loader import Watermark, main, read_rows, run

SAMPLE = Path(__file__).parent.parent / "sample" / "prices.csv"


def count(db):
    with sqlite3.connect(db) as c:
        return c.execute("SELECT COUNT(*) FROM prices").fetchone()[0]


def test_read_rows_cleans_and_skips_bad():
    rows = list(read_rows(SAMPLE))
    assert len(rows) == 4 and rows[0].ticker == "AAPL"


def test_first_run_loads_all_and_sets_watermark(tmp_path):
    out = run(SAMPLE, tmp_path / "p.db", tmp_path / "wm.json", batch_size=2)
    assert out["loaded"] == 4
    assert Watermark(tmp_path / "wm.json").get() == "2026-10-28T16:00:00"


def test_second_run_loads_nothing(tmp_path):
    db, wm = tmp_path / "p.db", tmp_path / "wm.json"
    run(SAMPLE, db, wm)
    assert run(SAMPLE, db, wm)["loaded"] == 0
    assert count(db) == 4


def test_only_new_rows_after_append(tmp_path):
    db, wm = tmp_path / "p.db", tmp_path / "wm.json"
    csv = tmp_path / "p.csv"
    csv.write_text(SAMPLE.read_text())
    run(csv, db, wm)
    with open(csv, "a") as f:
        f.write("AAPL,2026-10-29T16:00:00,235.00\n")
    out = run(csv, db, wm)
    assert out["loaded"] == 1 and count(db) == 5


def test_reset_watermark_rerun_is_idempotent(tmp_path):
    db, wm = tmp_path / "p.db", tmp_path / "wm.json"
    run(SAMPLE, db, wm)
    wm.unlink()
    run(SAMPLE, db, wm)  # upsert, so no duplicates
    assert count(db) == 4


def test_cli_missing_file_returns_2(tmp_path, capsys):
    assert main([str(tmp_path / "nope.csv")]) == 2
