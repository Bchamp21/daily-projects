"""Tiny Airflow-style DAG runner: dependencies, cycle check, parallel levels,
retries, skip-downstream on failure, results passed to children, resumable state."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

SUCCESS, FAILED, SKIPPED = "success", "failed", "skipped"


class CycleError(ValueError):
    pass


@dataclass
class Task:
    name: str
    fn: Callable[[dict[str, Any]], Any]  # receives {upstream_name: result}
    deps: list[str] = field(default_factory=list)
    retries: int = 0
    retry_delay: float = 0.0


class DAG:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def task(self, deps=(), retries=0, retry_delay=0.0, name=None):
        """Decorator: @dag.task(deps=["extract"])"""
        def wrap(fn):
            n = name or fn.__name__
            self.tasks[n] = Task(n, fn, list(deps), retries, retry_delay)
            return fn
        return wrap

    def levels(self) -> list[list[str]]:
        """Kahn's algorithm grouped into waves; tasks in one wave can run in parallel."""
        for t in self.tasks.values():
            for d in t.deps:
                if d not in self.tasks:
                    raise KeyError(f"{t.name} depends on unknown task {d}")
        indeg = {n: len(t.deps) for n, t in self.tasks.items()}
        children: dict[str, list[str]] = {n: [] for n in self.tasks}
        for t in self.tasks.values():
            for d in t.deps:
                children[d].append(t.name)
        wave = sorted(n for n, k in indeg.items() if k == 0)
        out, seen = [], 0
        while wave:
            out.append(wave)
            seen += len(wave)
            nxt = []
            for n in wave:
                for c in children[n]:
                    indeg[c] -= 1
                    if indeg[c] == 0:
                        nxt.append(c)
            wave = sorted(nxt)
        if seen != len(self.tasks):
            raise CycleError("cycle: " + " -> ".join(self._find_cycle()))
        return out

    def _find_cycle(self) -> list[str]:
        color: dict[str, int] = {}
        stack: list[str] = []

        def dfs(n):
            color[n] = 1
            stack.append(n)
            for d in self.tasks[n].deps:
                if color.get(d) == 1:
                    return stack[stack.index(d):] + [d]
                if d not in color and (c := dfs(d)):
                    return c
            color[n] = 2
            stack.pop()
            return None

        for n in sorted(self.tasks):
            if n not in color and (c := dfs(n)):
                return c[::-1]  # show in run order: dep -> child
        return []

    def run(self, state_path: str | Path | None = None, max_workers: int = 4,
            sleep=time.sleep) -> dict[str, dict]:
        """Run all tasks. With state_path, finished successes are skipped on rerun (resume)."""
        state: dict[str, dict] = {}
        if state_path and Path(state_path).exists():
            prev = json.loads(Path(state_path).read_text())
            state = {k: v for k, v in prev.items() if v["status"] == SUCCESS}

        def run_one(t: Task) -> dict:
            inputs = {d: state[d]["result"] for d in t.deps}
            for attempt in range(1, t.retries + 2):
                try:
                    return {"status": SUCCESS, "result": t.fn(inputs), "attempts": attempt}
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"
                    if attempt <= t.retries:
                        sleep(t.retry_delay * 2 ** (attempt - 1))
            return {"status": FAILED, "error": err, "attempts": attempt}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for wave in self.levels():
                todo = []
                for n in wave:
                    if n in state:
                        continue  # resumed
                    bad = [d for d in self.tasks[n].deps if state[d]["status"] != SUCCESS]
                    if bad:
                        state[n] = {"status": SKIPPED, "reason": f"upstream {bad[0]} not successful"}
                    else:
                        todo.append(n)
                for n, res in zip(todo, pool.map(lambda n: run_one(self.tasks[n]), todo)):
                    state[n] = res
                if state_path:
                    Path(state_path).write_text(json.dumps(state, indent=2, default=str))
        return state
