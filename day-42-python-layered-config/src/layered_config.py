"""Layered, typed config loader (12-factor style). Standard library only.

Precedence (lowest -> highest): defaults < TOML file < env vars < CLI overrides.
Every value is coerced to the declared type and validated; secrets are masked when printed.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping


class ConfigError(Exception):
    """Raised with ALL problems at once, so you fix them in one go."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class Setting:
    name: str                       # dotted key, e.g. "db.port"
    type: type                      # str, int, float, bool, list
    default: Any = None
    required: bool = False
    secret: bool = False
    choices: tuple | None = None
    check: Callable[[Any], bool] | None = None
    help: str = ""

    @property
    def env_name(self) -> str:      # "db.port" -> "APP_DB_PORT"
        return "APP_" + self.name.replace(".", "_").upper()


TRUE = {"1", "true", "yes", "on"}
FALSE = {"0", "false", "no", "off"}


def coerce(value: Any, typ: type) -> Any:
    """Turn strings from env/CLI (or TOML values) into the declared type."""
    if typ is bool:
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in TRUE:
            return True
        if s in FALSE:
            return False
        raise ValueError(f"not a boolean: {value!r}")
    if typ is int:
        if isinstance(value, bool):          # bool is a subclass of int: reject it
            raise ValueError(f"not an int: {value!r}")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"not an int: {value!r}")
        return int(str(value).strip()) if isinstance(value, str) else int(value)
    if typ is float:
        if isinstance(value, bool):
            raise ValueError(f"not a float: {value!r}")
        return float(value)
    if typ is list:
        if isinstance(value, list):
            return [str(v).strip() for v in value]
        return [p.strip() for p in str(value).split(",") if p.strip()]
    return str(value)


def _flatten(d: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, Mapping):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


@dataclass
class Config:
    values: dict[str, Any]
    sources: dict[str, str]          # where each value came from
    schema: dict[str, Setting] = field(repr=False, default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def masked(self) -> dict[str, Any]:
        out = {}
        for k, v in self.values.items():
            s = self.schema.get(k)
            out[k] = mask(v) if (s and s.secret and v) else v
        return out

    def explain(self) -> str:
        """One line per key: value (masked) and which layer won."""
        m = self.masked()
        return "\n".join(f"{k} = {m[k]!r}  <- {self.sources[k]}" for k in sorted(m))


def mask(v: Any) -> str:
    s = str(v)
    return "****" if len(s) <= 4 else "****" + s[-4:]


def load(
    schema: list[Setting],
    toml_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    cli: Mapping[str, Any] | None = None,
    strict: bool = True,
) -> Config:
    by_name = {s.name: s for s in schema}
    raw: dict[str, Any] = {}
    sources: dict[str, str] = {}
    problems: list[str] = []

    # 1) defaults
    for s in schema:
        if s.default is not None:
            raw[s.name], sources[s.name] = s.default, "default"

    # 2) TOML file
    if toml_path is not None:
        p = Path(toml_path)
        if p.exists():
            try:
                data = _flatten(tomllib.loads(p.read_text()))
            except tomllib.TOMLDecodeError as e:
                raise ConfigError([f"{p.name}: invalid TOML ({e})"]) from e
            for k, v in data.items():
                if k not in by_name:
                    if strict:
                        problems.append(f"unknown key in {p.name}: {k}")
                    continue
                if by_name[k].secret:
                    problems.append(f"secret {k} must not be in a file; use env {by_name[k].env_name}")
                    continue
                raw[k], sources[k] = v, f"file:{p.name}"

    # 3) environment variables
    env = env or {}
    for s in schema:
        if s.env_name in env:
            raw[s.name], sources[s.name] = env[s.env_name], f"env:{s.env_name}"

    # 4) CLI overrides (key=value)
    for k, v in (cli or {}).items():
        if k not in by_name:
            problems.append(f"unknown CLI key: {k}")
            continue
        raw[k], sources[k] = v, "cli"

    # coerce + validate every setting, collecting all problems
    values: dict[str, Any] = {}
    for s in schema:
        if s.name not in raw or raw[s.name] in ("", None):
            if s.required:
                problems.append(f"missing required {s.name} (set {s.env_name})")
            else:
                values[s.name] = None
                sources.setdefault(s.name, "unset")
            continue
        try:
            v = coerce(raw[s.name], s.type)
        except (ValueError, TypeError) as e:
            problems.append(f"{s.name} from {sources[s.name]}: {e}")
            continue
        if s.choices and v not in s.choices:
            problems.append(f"{s.name}={v!r} not in {list(s.choices)}")
            continue
        if s.check and not s.check(v):
            problems.append(f"{s.name}={(mask(v) if s.secret else v)!r} failed check ({s.help or 'rule'})")
            continue
        values[s.name] = v

    if problems:
        raise ConfigError(problems)
    return Config(values, {k: sources[k] for k in values}, by_name)


def parse_cli(args: list[str]) -> dict[str, str]:
    """['--set', 'db.port=6543', '--set', 'log.level=DEBUG'] -> dict"""
    out: dict[str, str] = {}
    it = iter(args)
    for a in it:
        if a == "--set":
            kv = next(it, "")
            if "=" not in kv:
                raise ConfigError([f"--set needs key=value, got {kv!r}"])
            k, v = kv.split("=", 1)
            out[k.strip()] = v
    return out

