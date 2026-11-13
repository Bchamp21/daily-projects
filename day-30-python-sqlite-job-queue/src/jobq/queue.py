"""Durable job queue on SQLite: enqueue, lease, ack, retry with backoff, dead-letter.

Pattern used by Celery/SQS/Airflow-style workers:
- A worker *leases* a job for `visibility_timeout` seconds instead of deleting it.
- If the worker crashes, the lease expires and another worker picks the job up.
- Failures retry with exponential backoff; after `max_attempts` the job goes to 'dead'.
- `dedupe_key` makes enqueue idempotent (same key twice = one job).
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    task          TEXT NOT NULL,
    payload       TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'ready',   -- ready | leased | done | dead
    attempts      INTEGER NOT NULL DEFAULT 0,
    max_attempts  INTEGER NOT NULL,
    run_after     REAL NOT NULL,
    lease_until   REAL,
    lease_token   TEXT,
    dedupe_key    TEXT UNIQUE,
    last_error    TEXT,
    created_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_jobs_ready ON jobs(status, run_after);
"""


@dataclass
class Job:
    id: str
    task: str
    payload: dict
    attempts: int
    lease_token: str


class JobQueue:
    def __init__(self, path: str = ":memory:", *, visibility_timeout: float = 30.0,
                 max_attempts: int = 3, base_backoff: float = 2.0,
                 clock: Callable[[], float] = time.time):
        self.db = sqlite3.connect(path, isolation_level=None)  # autocommit; we use explicit BEGIN
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.visibility_timeout = visibility_timeout
        self.max_attempts = max_attempts
        self.base_backoff = base_backoff
        self.clock = clock

    # ---------- producer ----------
    def enqueue(self, task: str, payload: dict[str, Any] | None = None, *,
                dedupe_key: str | None = None, delay: float = 0.0) -> str:
        job_id = uuid.uuid4().hex
        now = self.clock()
        cur = self.db.execute(
            "INSERT OR IGNORE INTO jobs(id, task, payload, max_attempts, run_after, dedupe_key, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (job_id, task, json.dumps(payload or {}), self.max_attempts, now + delay, dedupe_key, now),
        )
        if cur.rowcount == 0:  # duplicate dedupe_key -> return the existing job id
            return self.db.execute("SELECT id FROM jobs WHERE dedupe_key=?", (dedupe_key,)).fetchone()["id"]
        return job_id

    # ---------- consumer ----------
    def lease(self) -> Job | None:
        """Atomically claim one runnable job (ready, or leased but lease expired)."""
        now = self.clock()
        token = uuid.uuid4().hex
        self.db.execute("BEGIN IMMEDIATE")  # write lock: two workers can't claim the same row
        try:
            row = self.db.execute(
                "SELECT * FROM jobs WHERE (status='ready' AND run_after<=?)"
                " OR (status='leased' AND lease_until<=?)"
                " ORDER BY run_after, created_at LIMIT 1",
                (now, now),
            ).fetchone()
            if row is None:
                self.db.execute("COMMIT")
                return None
            self.db.execute(
                "UPDATE jobs SET status='leased', lease_until=?, lease_token=?, attempts=attempts+1 WHERE id=?",
                (now + self.visibility_timeout, token, row["id"]),
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return Job(row["id"], row["task"], json.loads(row["payload"]), row["attempts"] + 1, token)

    def ack(self, job: Job) -> bool:
        """Mark done. Returns False if our lease was lost (another worker took over)."""
        cur = self.db.execute(
            "UPDATE jobs SET status='done', lease_token=NULL WHERE id=? AND lease_token=? AND status='leased'",
            (job.id, job.lease_token),
        )
        return cur.rowcount == 1

    def fail(self, job: Job, error: str) -> str:
        """Retry with exponential backoff, or move to 'dead' after max_attempts. Returns new status."""
        row = self.db.execute("SELECT attempts, max_attempts, lease_token FROM jobs WHERE id=?",
                              (job.id,)).fetchone()
        if row is None or row["lease_token"] != job.lease_token:
            return "lease_lost"
        if row["attempts"] >= row["max_attempts"]:
            status, run_after = "dead", self.clock()
        else:
            status = "ready"
            run_after = self.clock() + self.base_backoff * 2 ** (row["attempts"] - 1)
        self.db.execute(
            "UPDATE jobs SET status=?, run_after=?, lease_token=NULL, lease_until=NULL, last_error=? WHERE id=?",
            (status, run_after, error[:500], job.id),
        )
        return status

    def requeue_dead(self, job_id: str) -> None:
        """Operator action: give a dead job a fresh set of attempts."""
        self.db.execute(
            "UPDATE jobs SET status='ready', attempts=0, run_after=?, last_error=NULL WHERE id=? AND status='dead'",
            (self.clock(), job_id),
        )

    # ---------- worker loop + stats ----------
    def work(self, handlers: dict[str, Callable[[dict], Any]], max_jobs: int = 100) -> int:
        """Process runnable jobs until none are left (or max_jobs). Returns jobs handled."""
        handled = 0
        while handled < max_jobs and (job := self.lease()) is not None:
            handled += 1
            handler = handlers.get(job.task)
            if handler is None:
                self.fail(job, f"no handler for task {job.task!r}")
                continue
            try:
                handler(job.payload)
            except Exception as exc:  # noqa: BLE001 - a worker must survive any task error
                self.fail(job, f"{type(exc).__name__}: {exc}")
            else:
                self.ack(job)
        return handled

    def stats(self) -> dict[str, int]:
        rows = self.db.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    def get(self, job_id: str) -> dict:
        return dict(self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
