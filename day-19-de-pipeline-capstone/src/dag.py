"""Tiny DAG runner: run tasks in dependency order, skip everything downstream of a failure."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Task:
    key: str
    fn: Callable[[dict], None]
    depends_on: list[str] = field(default_factory=list)
    notebook: str = ""          # path used in the Databricks job
    max_retries: int = 0


def topo_order(tasks: list[Task]) -> list[str]:
    """Kahn's algorithm. Raises on unknown deps or cycles."""
    by_key = {t.key: t for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            if d not in by_key:
                raise ValueError(f"{t.key} depends on unknown task {d}")
    indeg = {t.key: len(t.depends_on) for t in tasks}
    ready = [k for k in by_key if indeg[k] == 0]
    order: list[str] = []
    while ready:
        k = ready.pop(0)
        order.append(k)
        for t in tasks:
            if k in t.depends_on:
                indeg[t.key] -= 1
                if indeg[t.key] == 0:
                    ready.append(t.key)
    if len(order) != len(tasks):
        raise ValueError("cycle detected in DAG")
    return order


def run(tasks: list[Task], ctx: dict) -> dict[str, str]:
    """Returns {task: SUCCESS | FAILED | SKIPPED}."""
    by_key = {t.key: t for t in tasks}
    status: dict[str, str] = {}
    for key in topo_order(tasks):
        t = by_key[key]
        if any(status[d] != "SUCCESS" for d in t.depends_on):
            status[key] = "SKIPPED"
            continue
        for attempt in range(t.max_retries + 1):
            try:
                t.fn(ctx)
                status[key] = "SUCCESS"
                break
            except Exception as e:  # noqa: BLE001
                status[key] = "FAILED"
                ctx.setdefault("errors", {})[key] = str(e)
    return status
