"""Schema for the stock-pipeline app used across the daily projects."""
from layered_config import Setting

SCHEMA = [
    Setting("env", str, default="dev", choices=("dev", "test", "prod")),
    Setting("db.host", str, default="localhost"),
    Setting("db.port", int, default=5432, check=lambda p: 1 <= p <= 65535, help="1-65535"),
    Setting("db.name", str, default="market"),
    Setting("db.password", str, required=True, secret=True),
    Setting("api.key", str, secret=True, check=lambda k: len(k) >= 16, help="min 16 chars"),
    Setting("tickers", list, default=["AAPL", "MSFT"]),
    Setting("batch_size", int, default=500, check=lambda n: n > 0, help="> 0"),
    Setting("dry_run", bool, default=False),
    Setting("log.level", str, default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR")),
]

