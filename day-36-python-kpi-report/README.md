# Day 36 (Python): Monthly KPI report CLI (a Power BI matrix in plain Python)

Reads a trades CSV, rejects bad rows with reasons, and builds a monthly KPI table: revenue, trade count, MoM %, running total, top ticker. Standard library only. Picked to match the Data Analyst / Power BI job focus.

```mermaid
flowchart LR
  CSV[trades.csv] --> L[load_rows]
  L -->|bad shares/price| R[Rejected list]
  L -->|good rows| G[group by month]
  G --> K[KPIs: revenue, MoM %, running total, top ticker]
  K --> MD[Markdown table]
  R --> MD
  MD --> X{any rejected?}
  X -->|yes| E1[exit 1]
  X -->|no| E0[exit 0]
```

## Run

```bash
cd day-36-python-kpi-report
pip install -r requirements.txt
PYTHONPATH=src python3 -m kpi.cli data/trades.csv
pytest -q
```

## Key ideas (with the DAX twin)
| Python | DAX / Power BI |
|---|---|
| `defaultdict` group by month | matrix rows on Month |
| `safe_pct()` returns None on 0 base | `DIVIDE(cur - prev, prev)` |
| running sum over sorted months | `CALCULATE(SUM, DATESYTD)` / running total |
| rejected rows list | Power Query error rows |
| exit code 1 on bad data | refresh alert |
