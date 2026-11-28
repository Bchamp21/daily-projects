"""Databricks version (run in a notebook / job; not run by pytest).
Reads ticks from Bronze, builds 1-minute OHLC bars with a 30s watermark,
appends to Silver. Same rules as ohlc.py."""
from pyspark.sql import functions as F

CATALOG = spark.conf.get("market.catalog", "market_dev")  # noqa: F821 (spark is global in Databricks)

ticks = (
    spark.readStream.table(f"{CATALOG}.bronze.ticks")  # noqa: F821
    .where("price > 0 AND qty > 0")
    .withColumn("event_time", F.col("ts").cast("timestamp"))
    .withWatermark("event_time", "30 seconds")
    .dropDuplicatesWithinWatermark(["event_id"])   # DBR 13.3+/Spark 3.5
)

bars = (
    ticks.groupBy("ticker", F.window("event_time", "1 minute"))
    .agg(
        F.min_by("price", "event_time").alias("open"),
        F.max("price").alias("high"),
        F.min("price").alias("low"),
        F.max_by("price", "event_time").alias("close"),
        F.sum("qty").alias("volume"),
        (F.sum(F.col("price") * F.col("qty")) / F.sum("qty")).alias("vwap"),
        F.count("*").alias("trades"),
    )
    .select("ticker", F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"), "open", "high", "low",
            "close", "volume", F.round("vwap", 4).alias("vwap"), "trades")
)

(
    bars.writeStream.outputMode("append")
    .option("checkpointLocation", f"/Volumes/{CATALOG}/silver/checkpoints/ohlc_1m")
    .trigger(availableNow=True)
    .toTable(f"{CATALOG}.silver.ohlc_1m")
)
