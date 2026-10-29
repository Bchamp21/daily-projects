"""Safety checks on LLM-written SQL before it touches the database."""
import re

ALLOWED_TABLES = {"prices"}
BLOCKED = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|grant)\b", re.I
)


class UnsafeSQL(ValueError):
    pass


def check(sql: str, max_rows: int = 100) -> str:
    """Return a safe, row-limited SQL string or raise UnsafeSQL."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        raise UnsafeSQL("multiple statements are not allowed")
    if not re.match(r"^(select|with)\b", s, re.I):
        raise UnsafeSQL("only SELECT queries are allowed")
    if BLOCKED.search(s):
        raise UnsafeSQL("write/DDL keyword found")
    tables = {t.lower() for t in re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", s, re.I)}
    bad = tables - ALLOWED_TABLES
    if bad:
        raise UnsafeSQL(f"table not allowed: {sorted(bad)}")
    if not re.search(r"\blimit\s+\d+\s*$", s, re.I):
        s = f"{s} LIMIT {max_rows}"
    return s
