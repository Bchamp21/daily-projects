# Same idea with Structured Streaming: Spark keeps the checkpoint for you.
# Run in a Databricks notebook (spark is predefined there).
changes = (spark.readStream
           .option("readChangeFeed", "true")
           .table("main.market_silver.fact_prices"))

def fold(batch_df, batch_id):
    batch_df.createOrReplaceTempView("deltas_raw")
    # reuse the MERGE logic from 03_incremental_gold.sql against deltas_raw
    print(batch_id, batch_df.groupBy("_change_type").count().collect())

(changes.writeStream
   .foreachBatch(fold)
   .option("checkpointLocation", "/Volumes/main/market_gold/chk/ticker_summary")
   .trigger(availableNow=True)
   .start())
