from ohlc import OhlcStream, Tick


def T(i, ts, p, q=1, tk="AAPL"):
    return Tick(str(i), tk, ts, p, q)


def test_window_not_emitted_until_watermark_passes_end():
    s = OhlcStream(60, 30)
    assert s.process_batch([T(1, 10, 100)]) == []
    assert s.process_batch([T(2, 80, 101)]) == []      # wm=50 < 60
    out = s.process_batch([T(3, 90, 102)])              # wm=60 -> close [0,60)
    assert [(b.window_start, b.window_end) for b in out] == [(0, 60)]


def test_ohlc_values_and_vwap_out_of_order():
    s = OhlcStream(60, 30)
    s.process_batch([T(1, 30, 105, 2), T(2, 5, 100, 1), T(3, 50, 95, 1), T(4, 40, 110, 1)])
    out = s.process_batch([T(5, 200, 1)])
    b = out[0]
    assert (b.open, b.high, b.low, b.close) == (100, 110, 95, 95)
    assert b.volume == 5 and b.trades == 4
    assert b.vwap == round((210 + 100 + 95 + 110) / 5, 4)


def test_late_events_dropped_and_counted():
    s = OhlcStream(60, 30)
    s.process_batch([T(1, 100, 100)])                   # wm=70
    s.process_batch([T(2, 69, 99), T(3, 70, 101)])      # 69 late, 70 ok
    assert s.late_dropped == 1


def test_watermark_from_previous_batch_used_within_batch():
    s = OhlcStream(60, 30)
    # same batch: a far-future event must not make an earlier one late
    s.process_batch([T(1, 500, 100), T(2, 10, 100)])
    assert s.late_dropped == 0


def test_duplicates_dropped():
    s = OhlcStream(60, 30)
    s.process_batch([T("x", 10, 100, 5)])
    s.process_batch([T("x", 10, 100, 5)])
    out = s.process_batch([T("y", 200, 1)])
    assert s.dup_dropped == 1 and out[0].volume == 5


def test_each_window_emitted_once_and_state_cleaned():
    s = OhlcStream(60, 30)
    s.process_batch([T(1, 10, 1), T(2, 70, 1)])
    first = s.process_batch([T(3, 1000, 1)])
    assert len(first) == 2
    assert s.process_batch([T(4, 1001, 1)]) == []
    assert s.state_size() == 3   # open window [960,1020) + 2 dedupe ids


def test_bad_rows_and_multiple_tickers():
    s = OhlcStream(60, 0)
    s.process_batch([T(1, 1, 0), T(2, 2, 10, 0), T(3, 3, 10, tk="MSFT"), T(4, 4, 20)])
    out = s.process_batch([T(5, 60, 1)])
    assert s.bad_dropped == 2
    assert sorted(b.ticker for b in out) == ["AAPL", "MSFT"]
