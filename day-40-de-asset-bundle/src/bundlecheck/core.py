"""Lint a Databricks Asset Bundle before deploy: catch mistakes in CI, not at 6:30 PM."""
from __future__ import annotations
import re
from collections import deque
from pathlib import Path
import yaml

SECRET_RE = re.compile(r"(dapi[0-9a-f]{20,}|password\s*[:=]\s*\S+|token\s*[:=]\s*['\"]?[A-Za-z0-9]{16,})", re.I)
VAR_RE = re.compile(r"\$\{var\.([a-zA-Z_][\w]*)\}")


def load_bundle(root: str | Path) -> dict:
    """Read databricks.yml and merge every file matched by include:."""
    root = Path(root)
    cfg = yaml.safe_load((root / "databricks.yml").read_text()) or {}
    merged = {"resources": {"jobs": {}}}
    for pattern in cfg.get("include", []):
        for f in sorted(root.glob(pattern)):
            part = yaml.safe_load(f.read_text()) or {}
            merged["resources"]["jobs"].update(part.get("resources", {}).get("jobs", {}))
    cfg["resources"] = merged["resources"]
    return cfg


def task_order(tasks: list[dict]) -> list[str]:
    """Kahn topological sort. Raises ValueError on unknown deps or a cycle."""
    keys = {t["task_key"] for t in tasks}
    deps = {t["task_key"]: [d["task_key"] for d in t.get("depends_on", [])] for t in tasks}
    for k, ds in deps.items():
        for d in ds:
            if d not in keys:
                raise ValueError(f"{k} depends on unknown task {d}")
    indeg = {k: len(ds) for k, ds in deps.items()}
    q = deque(sorted(k for k, n in indeg.items() if n == 0))
    out = []
    while q:
        k = q.popleft()
        out.append(k)
        for child, ds in deps.items():
            if k in ds:
                indeg[child] -= 1
                if indeg[child] == 0:
                    q.append(child)
    if len(out) != len(keys):
        raise ValueError("cycle in tasks: " + ", ".join(sorted(keys - set(out))))
    return out


def check(cfg: dict, raw_text: str = "") -> list[str]:
    """Return a list of problems; empty list = safe to deploy."""
    problems: list[str] = []
    targets = cfg.get("targets", {})
    if "dev" not in targets or "prod" not in targets:
        problems.append("need both dev and prod targets")
    prod = targets.get("prod", {})
    if prod and prod.get("mode") != "production":
        problems.append("prod target must use mode: production")
    if prod and "run_as" not in prod:
        problems.append("prod must run_as a service principal, not a person")
    declared = set(cfg.get("variables", {}))
    for name in sorted(set(VAR_RE.findall(raw_text)) - declared):
        problems.append(f"variable used but not declared: {name}")
    if SECRET_RE.search(raw_text):
        problems.append("possible secret in bundle files; use secret scopes / env vars")
    jobs = cfg.get("resources", {}).get("jobs", {})
    if not jobs:
        problems.append("no jobs defined")
    for jname, job in jobs.items():
        tasks = job.get("tasks", [])
        try:
            task_order(tasks)
        except ValueError as e:
            problems.append(f"{jname}: {e}")
        if job.get("max_concurrent_runs", 1) != 1:
            problems.append(f"{jname}: max_concurrent_runs should be 1 for a daily load")
        if not job.get("email_notifications", {}).get("on_failure"):
            problems.append(f"{jname}: no on_failure alert")
        for t in tasks:
            if "timeout_seconds" not in t:
                problems.append(f"{jname}.{t['task_key']}: missing timeout_seconds")
    return problems


def check_dir(root: str | Path) -> list[str]:
    root = Path(root)
    raw = "\n".join(p.read_text() for p in [root / "databricks.yml", *sorted((root / "resources").glob("*.yml"))])
    return check(load_bundle(root), raw)
