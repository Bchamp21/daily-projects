import threading
import time

import pytest

from dagrun.dag import DAG, CycleError, FAILED, SKIPPED, SUCCESS



def test_levels_and_results_flow():
    d = DAG()
    d.task(name="a")(lambda _: 2)
    d.task(name="b")(lambda _: 3)
    d.task(name="c", deps=["a", "b"])(lambda up: up["a"] * up["b"])
    assert d.levels() == [["a", "b"], ["c"]]
    s = d.run()
    assert s["c"] == {"status": SUCCESS, "result": 6, "attempts": 1}


def test_cycle_detected_with_path():
    d = DAG()
    d.task(name="a", deps=["c"])(lambda _: 1)
    d.task(name="b", deps=["a"])(lambda _: 1)
    d.task(name="c", deps=["b"])(lambda _: 1)
    d.task(name="x")(lambda _: 1)
    with pytest.raises(CycleError) as e:
        d.levels()
    msg = str(e.value)
    assert all(n in msg for n in "abc") and "x" not in msg


def test_unknown_dep():
    d = DAG()
    d.task(name="a", deps=["ghost"])(lambda _: 1)
    with pytest.raises(KeyError):
        d.levels()


def test_retry_with_backoff_then_success():
    d = DAG()
    n = {"k": 0}

    def flaky(_):
        n["k"] += 1
        if n["k"] < 3:
            raise IOError("boom")
        return "ok"

    d.task(name="f", retries=3, retry_delay=1)(flaky)
    sleeps = []
    s = d.run(sleep=sleeps.append)
    assert s["f"]["status"] == SUCCESS and s["f"]["attempts"] == 3
    assert sleeps == [1, 2]


def test_failure_skips_downstream_only():
    d = DAG()
    d.task(name="bad")(lambda _: 1 / 0)
    d.task(name="good")(lambda _: 1)
    d.task(name="child", deps=["bad"])(lambda _: 1)
    d.task(name="grandchild", deps=["child", "good"])(lambda _: 1)
    d.task(name="other", deps=["good"])(lambda _: 1)
    s = d.run()
    assert s["bad"]["status"] == FAILED and "ZeroDivisionError" in s["bad"]["error"]
    assert s["child"]["status"] == SKIPPED
    assert s["grandchild"]["status"] == SKIPPED
    assert s["other"]["status"] == SUCCESS


def test_resume_skips_finished_tasks(tmp_path):
    st = tmp_path / "state.json"
    runs = {"a": 0, "b": 0}
    ok = {"b": False}

    def a(_):
        runs["a"] += 1
        return 10

    def b(up):
        runs["b"] += 1
        if not ok["b"]:
            raise RuntimeError("down")
        return up["a"] + 1

    d = DAG()
    d.task(name="a")(a)
    d.task(name="b", deps=["a"])(b)
    assert d.run(state_path=st)["b"]["status"] == FAILED
    ok["b"] = True
    s = d.run(state_path=st)
    assert s["b"]["result"] == 11
    assert runs == {"a": 1, "b": 2}  # a not rerun


def test_same_wave_runs_in_parallel():
    d = DAG()
    barrier = threading.Barrier(3, timeout=2)
    for n in "xyz":
        d.task(name=n)(lambda _: barrier.wait() is not None)
    t0 = time.time()
    s = d.run(max_workers=3)
    assert all(v["status"] == SUCCESS for v in s.values())
    assert time.time() - t0 < 2
