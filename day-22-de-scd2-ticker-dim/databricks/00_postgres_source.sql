-- Run in your LOCAL Postgres (same DB as Day 1 market.prices).
CREATE TABLE IF NOT EXISTS market.tickers (
  ticker        TEXT PRIMARY KEY,
  company_name  TEXT NOT NULL,
  sector        TEXT NOT NULL,
  exchange      TEXT NOT NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO market.tickers (ticker, company_name, sector, exchange) VALUES
  ('AAPL','Apple Inc.','Technology','NASDAQ'),
  ('META','Facebook Inc.','Technology','NASDAQ'),
  ('JHG','Janus Henderson Group','Financials','NYSE')
ON CONFLICT (ticker) DO NOTHING;
-- Later, simulate a change:
-- UPDATE market.tickers SET company_name='Meta Platforms Inc.', sector='Comm Services', updated_at=now() WHERE ticker='META';
