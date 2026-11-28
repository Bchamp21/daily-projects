from ohlc import OhlcStream, Tick

s = OhlcStream(window_s=60, delay_s=30)
batches = [
    [Tick("a", "AAPL", 0, 100, 10), Tick("b", "AAPL", 20, 102, 5), Tick("c", "AAPL", 45, 99, 5)],
    [Tick("d", "AAPL", 70, 101, 10), Tick("b", "AAPL", 20, 102, 5)],   # dup b
    [Tick("e", "AAPL", 95, 103, 10)],                                   # wm -> 65, closes 0-60
    [Tick("f", "AAPL", 30, 98, 1), Tick("g", "AAPL", 150, 104, 2)],     # f is late
]
for i, b in enumerate(batches, 1):
    out = s.process_batch(b)
    print(f"batch {i}: watermark={s.watermark} emitted={[(x.window_start, x.open, x.high, x.low, x.close, x.volume, x.vwap) for x in out]}")
print(f"late={s.late_dropped} dups={s.dup_dropped} state={s.state_size()}")
