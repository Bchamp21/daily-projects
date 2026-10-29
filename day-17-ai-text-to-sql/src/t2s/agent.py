"""Question -> SQL -> guard -> run -> (on error, feed error back and retry)."""
from dataclasses import dataclass, field

from .db import schema_text
from .guard import UnsafeSQL, check
from .llm import extract_sql

PROMPT = """You write SQLite SQL. Use only this schema:
{schema}
Return one SELECT statement, no explanation.
{feedback}QUESTION: {question}"""


@dataclass
class Result:
    ok: bool
    sql: str = ""
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    attempts: int = 0
    error: str = ""


def ask(question: str, llm, con, max_attempts: int = 3) -> Result:
    feedback = ""
    sql = ""
    for attempt in range(1, max_attempts + 1):
        prompt = PROMPT.format(schema=schema_text(), feedback=feedback, question=question)
        sql = extract_sql(llm.generate(prompt))
        try:
            safe = check(sql)
        except UnsafeSQL as e:
            # Never retry around a safety block: refuse.
            return Result(ok=False, sql=sql, attempts=attempt, error=f"blocked: {e}")
        try:
            cur = con.execute(safe)
            cols = [d[0] for d in cur.description]
            return Result(ok=True, sql=safe, columns=cols, rows=cur.fetchall(), attempts=attempt)
        except Exception as e:  # sqlite3.OperationalError etc.
            feedback = f"Your last SQL was:\n{sql}\nERROR: {e}\nFix it.\n"
    return Result(ok=False, sql=sql, attempts=max_attempts, error="gave up after retries")
