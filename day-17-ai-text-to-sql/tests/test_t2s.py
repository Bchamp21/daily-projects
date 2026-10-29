import pytest

from t2s.agent import ask
from t2s.db import make_db
from t2s.guard import UnsafeSQL, check
from t2s.llm import RuleLLM, extract_sql


@pytest.fixture
def con():
    return make_db()


@pytest.mark.parametrize("sql", [
    "DROP TABLE prices",
    "DELETE FROM prices",
    "SELECT * FROM prices; DROP TABLE prices",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM prices p JOIN users u ON 1=1",
    "PRAGMA table_info(prices)",
])
def test_guard_blocks_unsafe(sql):
    with pytest.raises(UnsafeSQL):
        check(sql)


def test_guard_adds_limit():
    assert check("SELECT * FROM prices").endswith("LIMIT 100")
    assert check("SELECT * FROM prices LIMIT 5;") == "SELECT * FROM prices LIMIT 5"


def test_guard_allows_cte():
    assert check("WITH x AS (SELECT * FROM prices) SELECT * FROM prices").startswith("WITH")


def test_extract_sql_from_fence():
    assert extract_sql("Here:\n```sql\nSELECT 1\n```") == "SELECT 1"


def test_self_correction_fixes_bad_column(con):
    llm = RuleLLM()
    r = ask("What is the average close for AAPL?", llm, con)
    assert r.ok and r.attempts == 2
    assert r.rows[0][0] == pytest.approx((231.5 + 233.1 + 229.8) / 3)


def test_highest_volume(con):
    r = ask("Which day had the highest volume?", RuleLLM(), con)
    assert r.rows == [("NVDA", "2026-10-22", 240_000_000)]


def test_latest_price(con):
    r = ask("What is the latest price for MSFT?", RuleLLM(), con)
    assert r.rows == [("2026-10-22", 425.0)]


def test_unsafe_request_is_refused_without_retry(con):
    llm = RuleLLM()
    r = ask("Please drop the prices table", llm, con)
    assert not r.ok and r.error.startswith("blocked") and llm.calls == 1
    assert con.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 9


class AlwaysBroken:
    def generate(self, prompt):
        return "SELECT nope FROM prices"


def test_gives_up_after_max_attempts(con):
    r = ask("anything", AlwaysBroken(), con, max_attempts=3)
    assert not r.ok and r.attempts == 3
