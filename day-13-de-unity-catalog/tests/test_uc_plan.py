from pathlib import Path

import pytest
import yaml

import uc_plan

CFG = yaml.safe_load((Path(__file__).parent.parent / "governance.yml").read_text())


def test_config_is_valid():
    assert uc_plan.validate(CFG) == []


def test_sql_is_idempotent_and_ordered():
    sql = uc_plan.build_sql(CFG)
    assert sql[0] == "CREATE CATALOG IF NOT EXISTS `market`;"
    assert all("IF NOT EXISTS" in s or "OR REPLACE" in s or s.startswith(("GRANT", "ALTER"))
               for s in sql)
    # a mask function must be created before it is attached
    create = next(i for i, s in enumerate(sql) if "mask_volume`(v BIGINT)" in s)
    attach = next(i for i, s in enumerate(sql) if "SET MASK" in s)
    assert create < attach


def test_bi_readers_only_on_gold():
    sql = "\n".join(uc_plan.build_sql(CFG))
    assert "ON SCHEMA `market`.`gold` TO `bi_readers`" in sql
    assert "ON SCHEMA `market`.`silver` TO `bi_readers`" not in sql


def test_row_filter_sql():
    sql = "\n".join(uc_plan.build_sql(CFG))
    assert "val IN ('AAPL', 'MSFT')" in sql
    assert "SET ROW FILTER `market`.`silver`.`ticker_region_filter` ON (`ticker`)" in sql


@pytest.mark.parametrize("groups,table,ticker,expected", [
    ({"bi_readers"}, "gold.gold_ticker_summary", "AAPL", True),
    ({"bi_readers"}, "silver.prices", "AAPL", False),       # no silver grant
    ({"analysts", "analysts_us"}, "silver.prices", "AAPL", True),
    ({"analysts", "analysts_us"}, "silver.prices", "TSLA", False),  # row filtered
    ({"data_engineers"}, "silver.prices", "TSLA", True),    # wildcard
    ({"nobody"}, "gold.gold_ticker_summary", "AAPL", False),
])
def test_access_simulator(groups, table, ticker, expected):
    assert uc_plan.can_see(CFG, groups, table, ticker) is expected


def test_bad_privilege_is_caught():
    bad = {**CFG, "catalog_grants": {"analysts": ["SELEKT"]}}
    assert any("SELEKT" in e for e in uc_plan.validate(bad))


def test_cli_writes_file(tmp_path):
    out = tmp_path / "plan.sql"
    cfg = Path(__file__).parent.parent / "governance.yml"
    assert uc_plan.main([str(cfg), "-o", str(out)]) == 0
    assert "GRANT" in out.read_text()
