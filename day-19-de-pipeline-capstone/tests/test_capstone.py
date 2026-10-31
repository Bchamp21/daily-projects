from pathlib import Path
import pytest

import dag
from bundle import to_bundle_yaml
from pipeline import build_tasks, new_context, ingest_bronze, build_silver, build_gold

DATA = Path(__file__).resolve().parent.parent / "data/source_prices.csv"


def ok(ctx):
    ctx.setdefault("ran", []).append("x")


def boom(ctx):
    raise RuntimeError("boom")


def test_topo_order_respects_deps():
    ts = [dag.Task("c", ok, ["b"]), dag.Task("a", ok), dag.Task("b", ok, ["a"])]
    assert dag.topo_order(ts) == ["a", "b", "c"]


def test_cycle_detected():
    with pytest.raises(ValueError, match="cycle"):
        dag.topo_order([dag.Task("a", ok, ["b"]), dag.Task("b", ok, ["a"])])


def test_unknown_dep():
    with pytest.raises(ValueError, match="unknown"):
        dag.topo_order([dag.Task("a", ok, ["zzz"])])


def test_failure_skips_downstream():
    ts = [dag.Task("a", ok), dag.Task("b", boom, ["a"]), dag.Task("c", ok, ["b"]), dag.Task("d", ok, ["a"])]
    st = dag.run(ts, {})
    assert st == {"a": "SUCCESS", "b": "FAILED", "d": "SUCCESS", "c": "SKIPPED"}


def test_retry_then_success():
    calls = {"n": 0}

    def flaky(ctx):
        calls["n"] += 1
        if calls["n"] < 3:
            raise IOError("network")

    assert dag.run([dag.Task("f", flaky, max_retries=2)], {}) == {"f": "SUCCESS"}
    assert calls["n"] == 3


def test_full_pipeline_success():
    ctx = new_context(DATA)
    st = dag.run(build_tasks(), ctx)
    assert set(st.values()) == {"SUCCESS"}
    con = ctx["con"]
    assert con.execute("SELECT COUNT(*) FROM bronze_prices").fetchone()[0] == 10  # raw, untouched
    assert con.execute("SELECT COUNT(*) FROM silver_prices").fetchone()[0] == 8   # 1 dup + 1 bad removed
    assert ctx["quarantined"] == 1
    gold = dict(con.execute("SELECT ticker, last_close FROM gold_ticker_summary").fetchall())
    assert gold == {"AAPL": 225.2, "MSFT": 416.0}


def test_silver_return_math():
    ctx = new_context(DATA)
    dag.run(build_tasks(), ctx)
    r = ctx["con"].execute(
        "SELECT daily_return FROM silver_prices WHERE ticker='AAPL' AND trade_date='2026-10-02'").fetchone()[0]
    assert r == pytest.approx(227.40 / 226.80 - 1, abs=1e-6)


def test_rerun_is_idempotent_for_silver_and_gold():
    ctx = new_context(DATA)
    dag.run(build_tasks(), ctx)
    ctx["batch_id"] = "b2"
    dag.run(build_tasks(), ctx)
    con = ctx["con"]
    assert con.execute("SELECT COUNT(*) FROM bronze_prices").fetchone()[0] == 20  # bronze appends
    assert con.execute("SELECT COUNT(*) FROM silver_prices").fetchone()[0] == 8   # silver stays clean


def test_quality_gate_fails_and_reports():
    ctx = new_context(DATA)
    tasks = build_tasks()
    dag.run(tasks, ctx)
    ctx["con"].execute("INSERT INTO silver_prices VALUES ('AAPL','2026-10-01',1,1,1,1,1,NULL,NULL)")
    from pipeline import quality_gate
    with pytest.raises(AssertionError):
        quality_gate(ctx)
    assert "silver_unique_key" in ctx["checks_failed"]


def test_bundle_matches_dag():
    y = to_bundle_yaml(build_tasks())
    for t in build_tasks():
        assert f"task_key: {t.key}" in y
    assert y.count("depends_on:") == 4
    assert "timezone_id: America/Denver" in y
    assert "max_retries: 2" in y


def test_committed_bundle_is_up_to_date():
    committed = (Path(__file__).resolve().parent.parent / "bundle/databricks.yml").read_text()
    assert committed == to_bundle_yaml(build_tasks()), "run: python src/main.py bundle"


def test_cli_run_exit_code():
    from main import main
    assert main(["run"]) == 0
