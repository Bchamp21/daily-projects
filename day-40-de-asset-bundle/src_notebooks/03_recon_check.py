# Databricks notebook source
catalog = dbutils.widgets.get("catalog")
src = spark.sql("SELECT count(*) c FROM postgres_market.market.prices").first().c
tgt = spark.sql(f"SELECT count(*) c FROM {catalog}.silver.prices").first().c
assert tgt >= src, f"Silver has {tgt} rows, source has {src}"  # fails the task -> dbt_gold skipped
