-- Preview, then delete tombstoned files older than 7 days.
VACUUM main.market_silver.fact_prices RETAIN 168 HOURS DRY RUN;
VACUUM main.market_silver.fact_prices RETAIN 168 HOURS;
-- Time travel older than 7 days will now fail. That is expected.
