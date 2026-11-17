-- Pass/fail counts per expectation from the pipeline event log.
SELECT
  e.timestamp,
  exp.name,
  exp.dataset,
  exp.passed_records,
  exp.failed_records
FROM event_log(TABLE(main.market.silver_prices)) e
LATERAL VIEW explode(from_json(
  e.details:flow_progress:data_quality:expectations,
  'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>'
)) AS exp
WHERE e.event_type = 'flow_progress'
ORDER BY e.timestamp DESC;
