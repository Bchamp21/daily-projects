-- Keep a history of every recon run (good audit evidence).
CREATE TABLE IF NOT EXISTS main.market.recon_log (
  run_ts TIMESTAMP, check_name STRING, status STRING, detail STRING);

INSERT INTO main.market.recon_log
SELECT current_timestamp(), 'row_count',
       CASE WHEN s.n = t.n THEN 'PASS' ELSE 'FAIL' END,
       concat('source=', s.n, ' target=', t.n)
FROM (SELECT count(*) n FROM src) s CROSS JOIN (SELECT count(*) n FROM tgt) t;

-- Fail the job task if anything failed today (Workflows marks the task red).
SELECT assert_true(count_if(status = 'FAIL') = 0, 'Recon failed: see main.market.recon_log')
FROM main.market.recon_log WHERE run_ts >= current_date();
