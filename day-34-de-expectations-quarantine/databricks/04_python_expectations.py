# Same rules in Python (Lakeflow pipelines). Use in a pipeline notebook/file.
import dlt

DROP_RULES = {
    "ticker_present": "ticker IS NOT NULL AND ticker <> ''",
    "positive_close": "close > 0",
    "high_ge_low": "high >= low",
}

@dlt.table(name="silver_prices")
@dlt.expect_all_or_drop(DROP_RULES)
@dlt.expect("volume_not_negative", "volume >= 0")
@dlt.expect_or_fail("valid_date", "trade_date IS NOT NULL")
def silver_prices():
    return dlt.read("bronze_prices")

@dlt.table(name="quarantine_prices")
def quarantine_prices():
    bad = " OR ".join(f"NOT coalesce({c}, false)" for c in DROP_RULES.values())
    return dlt.read("bronze_prices").where(bad)
