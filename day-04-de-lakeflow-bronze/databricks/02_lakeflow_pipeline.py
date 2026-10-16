# Databricks notebook / Declarative Pipeline (DLT) stub — NOT imported locally.
# Paste into a Databricks pipeline notebook. Requires DLT / Lakeflow runtime.
#
# Lakeflow Connect  → managed CDC/ingest from databases (Postgres, etc.)
# DLT / Declarative Pipelines → @dlt.table transforms you own (this stub)
#
# Secrets (create a scope, e.g. `market-pg`):
#   POSTGRES_JDBC_URL, POSTGRES_USER, POSTGRES_PASSWORD
# Never hardcode credentials.

# pyright: reportMissingImports=false
try:
    import dlt  # provided by Databricks pipeline runtime
    from pyspark.sql import functions as F
except ImportError:
    # Local import of this file is unsupported — Databricks only.
    dlt = None  # type: ignore
    F = None  # type: ignore


# --- Option A: JDBC read from Postgres market.prices (staging → bronze) ---
# Uncomment when secrets + JDBC driver are configured in the workspace.
#
# @dlt.table(
#     name="prices",
#     comment="Bronze market.prices from Postgres JDBC",
#     table_properties={"quality": "bronze"},
# )
# def prices():
#     url = dbutils.secrets.get("market-pg", "POSTGRES_JDBC_URL")
#     user = dbutils.secrets.get("market-pg", "POSTGRES_USER")
#     password = dbutils.secrets.get("market-pg", "POSTGRES_PASSWORD")
#     raw = (
#         spark.read.format("jdbc")
#         .option("url", url)
#         .option("dbtable", "market.prices")
#         .option("user", user)
#         .option("password", password)
#         .option("driver", "org.postgresql.Driver")
#         .load()
#     )
#     return (
#         raw
#         .withColumn("ticker", F.upper(F.col("ticker")))
#         .withColumn("_ingested_at", F.current_timestamp())
#         .withColumn("_source_system", F.lit("postgres.market.prices"))
#         .withColumn("_batch_id", F.lit(spark.conf.get("pipeline.update_id", "manual")))
#         # Prefer the Python normalize + hash from this repo for parity;
#         # or implement an equivalent Spark expression for _source_row_hash.
#     )


# --- Option B: read a staging volume / JSONL landed by an external job ---
if dlt is not None:

    @dlt.table(
        name="prices_from_volume",
        comment="Bronze from /Volumes/.../bronze/prices.jsonl (local-demo parity)",
        table_properties={"quality": "bronze"},
    )
    def prices_from_volume():
        # Replace path with your UC Volume after uploading data/bronze/prices.jsonl
        path = "/Volumes/main/market_bronze/landing/prices.jsonl"
        return (
            spark.read.json(path)  # noqa: F821 — spark in Databricks
            .withColumn("_ingested_at", F.coalesce(F.col("_ingested_at"), F.current_timestamp()))
        )
