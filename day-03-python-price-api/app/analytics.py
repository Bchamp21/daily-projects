"""Pure functions: easy to unit test, no web or DB needed."""


def simple_moving_average(closes: list[float], window: int) -> list[float | None]:
    """SMA per row; None until there are `window` values."""
    if window < 1:
        raise ValueError("window must be >= 1")
    out: list[float | None] = []
    running = 0.0
    for i, c in enumerate(closes):
        running += c
        if i >= window:
            running -= closes[i - window]
        out.append(round(running / window, 4) if i + 1 >= window else None)
    return out
