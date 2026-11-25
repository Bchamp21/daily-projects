# Databricks notebook source
catalog = dbutils.widgets.get("catalog")
spark.sql(f"""MERGE INTO {catalog}.silver.prices t
USING (SELECT DISTINCT upper(trim(ticker)) ticker, trade_date, close FROM {catalog}.bronze.prices_raw) s
ON t.ticker = s.ticker AND t.trade_date = s.trade_date
WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")
