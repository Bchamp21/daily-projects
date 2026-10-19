# Databricks notebook source
# Day 7: Bronze -> Silver with PySpark + Delta MERGE.
# Run on a Databricks cluster or serverless notebook (needs Spark + Delta).
# Local tests cover the same logic in src/silver/transform.py.

from delta.tables import DeltaTable
from pyspark.sql import Window
from pyspark.sql import functions as F

CATALOG = spark.conf.get("market.catalog", "main")  # noqa: F821  (spark is provided by Databricks)
BRONZE = f"{CATALOG}.market_bronze.prices"
SILVER = f"{CATALOG}.market_silver.prices"

# COMMAND ----------
# 1) Dedupe: one row per (ticker, trade_date), latest _ingested_at wins
bronze = spark.table(BRONZE)  # noqa: F821
w_latest = Window.partitionBy("ticker", "trade_date").orderBy(F.col("_ingested_at").desc())
latest = (
    bronze.withColumn("_rn", F.row_number().over(w_latest))
    .filter("_rn = 1")
    .drop("_rn")
)

# COMMAND ----------
# 2) Derived columns per ticker in date order
w_ticker = Window.partitionBy("ticker").orderBy("trade_date")
silver_src = (
    latest.withColumn("prev_close", F.lag("close").over(w_ticker))
    .withColumn("daily_return", F.round((F.col("close") - F.col("prev_close")) / F.col("prev_close"), 6))
    .withColumn("price_range", F.round(F.col("high") - F.col("low"), 6))
    .withColumn("_silver_updated_at", F.current_timestamp())
    .select(
        "ticker", "trade_date", "open", "high", "low", "close", "volume",
        "prev_close", "daily_return", "price_range",
        "_source_row_hash", "_ingested_at", "_silver_updated_at",
    )
)

# COMMAND ----------
# 3) MERGE: update only when the row really changed, insert new keys
(
    DeltaTable.forName(spark, SILVER)  # noqa: F821
    .alias("t")
    .merge(silver_src.alias("s"), "t.ticker = s.ticker AND t.trade_date = s.trade_date")
    .whenMatchedUpdateAll(condition="t._source_row_hash <> s._source_row_hash OR t.prev_close IS DISTINCT FROM s.prev_close")
    .whenNotMatchedInsertAll()
    .execute()
)

# COMMAND ----------
display(spark.sql(f"DESCRIBE HISTORY {SILVER} LIMIT 5"))  # noqa: F821
display(spark.table(SILVER).orderBy("ticker", "trade_date"))  # noqa: F821
