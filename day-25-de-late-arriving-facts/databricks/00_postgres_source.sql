-- On-prem source for late price corrections. Day 1 loaded market.prices;
-- this table is the restatement feed: one publish per (ticker, trade_date, published_at).
CREATE SCHEMA IF NOT EXISTS market;

CREATE TABLE IF NOT EXISTS market.price_events (
  ticker        TEXT        NOT NULL,
  trade_date    DATE        NOT NULL,
  close         NUMERIC(18, 4) NOT NULL,
  published_at  TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (ticker, trade_date, published_at)
);

INSERT INTO market.price_events (ticker, trade_date, close, published_at) VALUES
  ('AAPL', DATE '2026-10-03', 178.50, TIMESTAMPTZ '2026-10-03 21:00:00+00'),
  ('MSFT', DATE '2026-10-03', 420.00, TIMESTAMPTZ '2026-10-03 21:00:00+00'),
  ('AAPL', DATE '2026-10-04', 180.00, TIMESTAMPTZ '2026-10-04 21:00:00+00'),
  ('MSFT', DATE '2026-10-04', 422.00, TIMESTAMPTZ '2026-10-04 21:00:00+00'),
  -- vendor restates AAPL's Oct 3 close two days later
  ('AAPL', DATE '2026-10-03', 177.20, TIMESTAMPTZ '2026-10-06 08:15:00+00'),
  ('AAPL', DATE '2026-10-06', 181.10, TIMESTAMPTZ '2026-10-06 21:00:00+00'),
  ('MSFT', DATE '2026-10-06', 419.50, TIMESTAMPTZ '2026-10-06 21:00:00+00'),
  -- older than the 3-day lateness window once watermark is 2026-10-04
  ('AAPL', DATE '2026-09-20', 170.00, TIMESTAMPTZ '2026-10-06 08:00:00+00')
ON CONFLICT DO NOTHING;
