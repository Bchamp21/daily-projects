import pytest

from app.analytics import simple_moving_average


def test_sma_basic():
    assert simple_moving_average([1, 2, 3, 4], 2) == [None, 1.5, 2.5, 3.5]


def test_sma_window_one_is_identity():
    assert simple_moving_average([5.0, 6.0], 1) == [5.0, 6.0]


def test_sma_bad_window():
    with pytest.raises(ValueError):
        simple_moving_average([1, 2], 0)
