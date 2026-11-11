import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdf_gold import CdfConsumer, DeltaTable, full_recompute


def test_insert_update_delete_change_types():
    t = DeltaTable()
    t.commit({("AAPL", "d1"): 10.0})
    t.commit({("AAPL", "d1"): 12.0})
    t.commit(deletes=[("AAPL", "d1")])
    types = [c["_change_type"] for c in t.changes]
    assert types == ["insert", "update_preimage", "update_postimage", "delete"]
    assert [c["_commit_version"] for c in t.changes] == [1, 2, 2, 3]


def test_same_value_upsert_logs_nothing():
    t = DeltaTable()
    t.commit({("AAPL", "d1"): 10.0})
    t.commit({("AAPL", "d1"): 10.0})
    assert len(t.changes) == 1


def test_incremental_gold_and_checkpoint():
    t, c = DeltaTable(), CdfConsumer()
    t.commit({("AAPL", "d1"): 10.0, ("AAPL", "d2"): 20.0})
    assert c.run(t) == 2
    assert c.gold["AAPL"] == {"row_count": 2, "sum_close": 30.0, "avg_close": 15.0}
    t.commit({("AAPL", "d2"): 30.0})
    assert c.run(t) == 2  # pre + post image only, not the whole table
    assert c.gold["AAPL"]["avg_close"] == 20.0
    assert c.checkpoint == 2


def test_rerun_is_idempotent():
    t, c = DeltaTable(), CdfConsumer()
    t.commit({("AAPL", "d1"): 10.0})
    c.run(t)
    before = dict(c.gold["AAPL"])
    assert c.run(t) == 0
    assert c.gold["AAPL"] == before


def test_ticker_removed_when_all_rows_deleted():
    t, c = DeltaTable(), CdfConsumer()
    t.commit({("MSFT", "d1"): 400.0})
    c.run(t)
    t.commit(deletes=[("MSFT", "d1")])
    c.run(t)
    assert "MSFT" not in c.gold


def test_random_history_matches_full_recompute():
    rng = random.Random(28)
    t, c = DeltaTable(), CdfConsumer()
    keys = [(tk, f"d{i}") for tk in ("AAPL", "MSFT", "NVDA") for i in range(5)]
    for step in range(40):
        ups = {k: float(rng.randint(100, 110)) for k in rng.sample(keys, 3)}
        dels = rng.sample(keys, 1) if step % 4 == 0 else []
        t.commit(ups, dels)
        if step % 3 == 0:
            c.run(t)
    c.run(t)
    assert c.gold == full_recompute(t)
