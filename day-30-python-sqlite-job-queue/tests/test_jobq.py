import pytest

from jobq import JobQueue


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def q(clock):
    return JobQueue(clock=clock, visibility_timeout=10, max_attempts=3, base_backoff=2)


def test_enqueue_lease_ack(q):
    jid = q.enqueue("t", {"x": 1})
    job = q.lease()
    assert job.id == jid and job.payload == {"x": 1} and job.attempts == 1
    assert q.lease() is None  # leased jobs are invisible
    assert q.ack(job)
    assert q.stats() == {"done": 1}


def test_dedupe_key_is_idempotent(q):
    a = q.enqueue("t", {}, dedupe_key="k")
    b = q.enqueue("t", {}, dedupe_key="k")
    assert a == b and q.stats() == {"ready": 1}


def test_delay(q, clock):
    q.enqueue("t", delay=5)
    assert q.lease() is None
    clock.t += 5
    assert q.lease() is not None


def test_expired_lease_is_reclaimed_and_old_ack_rejected(q, clock):
    q.enqueue("t")
    first = q.lease()
    clock.t += 11  # worker 1 "crashed": lease expired
    second = q.lease()
    assert second.id == first.id and second.attempts == 2
    assert not q.ack(first)  # stale token
    assert q.fail(first, "late") == "lease_lost"
    assert q.ack(second)


def test_backoff_then_dead_letter(q, clock):
    jid = q.enqueue("t")
    job = q.lease()
    assert q.fail(job, "boom") == "ready"
    assert q.get(jid)["run_after"] == clock.t + 2  # 2 * 2**0
    assert q.lease() is None
    clock.t += 2
    job = q.lease()
    assert q.fail(job, "boom") == "ready"
    assert q.get(jid)["run_after"] == clock.t + 4  # 2 * 2**1
    clock.t += 4
    job = q.lease()
    assert q.fail(job, "boom again") == "dead"
    row = q.get(jid)
    assert row["status"] == "dead" and row["last_error"] == "boom again"
    q.requeue_dead(jid)
    assert q.lease().attempts == 1


def test_work_loop_with_flaky_and_unknown_tasks(q, clock):
    calls = {"n": 0}

    def flaky(p):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("slow")

    q.enqueue("flaky")
    q.enqueue("ok")
    q.enqueue("nope")
    assert q.work({"flaky": flaky, "ok": lambda p: None}) == 3
    assert q.stats() == {"done": 1, "ready": 2}
    for _ in range(3):
        clock.t += 10
        q.work({"flaky": flaky, "ok": lambda p: None})
    assert q.stats() == {"done": 2, "dead": 1}


def test_survives_restart_on_disk(tmp_path, clock):
    path = str(tmp_path / "jobs.db")
    JobQueue(path, clock=clock).enqueue("t", {"ticker": "AAPL"})
    job = JobQueue(path, clock=clock).lease()  # new process, same file
    assert job.payload == {"ticker": "AAPL"}
