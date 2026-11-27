"""Run: python3 demo.py --set log.level=DEBUG
Reads config.toml, then APP_* env vars, then --set overrides, and prints where each value came from."""
import os
import sys

sys.path.insert(0, "src")
from app_schema import SCHEMA  # noqa: E402
from layered_config import ConfigError, load, parse_cli  # noqa: E402

env = dict(os.environ)
env.setdefault("APP_DB_PASSWORD", "demo-only-password")  # real runs: export it, never commit it
env.setdefault("APP_TICKERS", "AAPL,MSFT,NVDA")
try:
    cfg = load(SCHEMA, "config.toml", env=env, cli=parse_cli(sys.argv[1:]))
except ConfigError as e:
    print("Config errors:")
    for p in e.problems:
        print("  -", p)
    sys.exit(2)
print(cfg.explain())

