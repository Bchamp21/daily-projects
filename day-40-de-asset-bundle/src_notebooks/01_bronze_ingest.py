# Databricks notebook source
catalog = dbutils.widgets.get("catalog")
spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.bronze.prices_raw AS SELECT * FROM postgres_market.market.prices WHERE 1=0")
spark.sql(f"INSERT INTO {catalog}.bronze.prices_raw SELECT *, current_timestamp() AS _ingested_at FROM postgres_market.market.prices")
