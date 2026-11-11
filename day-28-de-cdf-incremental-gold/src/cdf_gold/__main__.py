from .core import CdfConsumer, DeltaTable, full_recompute

t = DeltaTable()
c = CdfConsumer()
t.commit({("AAPL", "2026-11-02"): 220.0, ("AAPL", "2026-11-03"): 222.0,
          ("MSFT", "2026-11-02"): 410.0})
print("run 1 used", c.run(t), "changes ->", c.gold)
t.commit({("AAPL", "2026-11-03"): 224.0, ("MSFT", "2026-11-03"): 412.0})  # correction + new
t.commit(deletes=[("MSFT", "2026-11-02")])                                 # bad row removed
print("run 2 used", c.run(t), "changes ->", c.gold)
print("run 3 used", c.run(t), "changes (nothing new)")
print("checkpoint version:", c.checkpoint)
print("matches full recompute:", c.gold == full_recompute(t))
