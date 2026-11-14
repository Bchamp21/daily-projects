import random
from .core import (DeltaTable, MB, health, plan_optimize, apply_optimize,
                   plan_vacuum, apply_vacuum, render_sql)

rng = random.Random(7)
t = DeltaTable("main.market_silver.fact_prices")
# streaming micro-batches -> many tiny files
for hour in range(48):
    for d in ("trade_date=2026-11-12", "trade_date=2026-11-13"):
        t.add(d, rng.randint(1, 8) * MB, now=hour)

print("before :", health(t))
bins = plan_optimize(t)
apply_optimize(t, bins, now=50)
print(f"OPTIMIZE rewrote {sum(len(b.files) for b in bins)} files into {len(bins)}")
print("after  :", health(t))
print("vacuum day 3 :", len(plan_vacuum(t, now=72)), "files (too new, kept)")
n = apply_vacuum(t, plan_vacuum(t, now=50 + 169))
print("vacuum day 9 :", n, "files deleted")
print()
print(render_sql(t.name, bins, 168))
