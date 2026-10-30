"""Reusable building blocks: a retry decorator, a timing decorator, and batching."""
from __future__ import annotations

import functools
import logging
import time
from itertools import islice
from typing import Callable, Iterable, Iterator, TypeVar

T = TypeVar("T")
log = logging.getLogger("incload")


def retry(times: int = 3, delay: float = 0.1, exceptions: tuple = (Exception,),
          sleep: Callable[[float], None] = time.sleep):
    """Retry a function on the given exceptions with exponential backoff."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    if attempt == times:
                        raise
                    wait = delay * 2 ** (attempt - 1)
                    log.warning("%s failed (%s); retry %d in %.2fs", fn.__name__, exc, attempt, wait)
                    sleep(wait)
        return wrapper
    return decorator


def timed(fn):
    """Log how long a call took and stash it on wrapper.last_seconds."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            wrapper.last_seconds = time.perf_counter() - start
            log.info("%s took %.4fs", fn.__name__, wrapper.last_seconds)
    wrapper.last_seconds = 0.0
    return wrapper


def batched(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield lists of up to `size` items without loading everything in memory."""
    if size < 1:
        raise ValueError("size must be >= 1")
    it = iter(items)
    while chunk := list(islice(it, size)):
        yield chunk
