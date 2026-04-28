from datetime import date

import pytest

from math_engine.expiration import NoSuitableExpirationError, pick_expiration


def test_picks_friday_within_13_to_16_day_window():
    today = date(2026, 4, 25)
    available = [date(2026, 5, 1), date(2026, 5, 8), date(2026, 5, 15)]
    assert pick_expiration(today=today, available=available) == date(2026, 5, 8)


def test_prefers_closest_to_14_day_target():
    today = date(2026, 4, 25)
    available = [date(2026, 5, 8), date(2026, 5, 9)]  # 13d and 14d
    # Both within 13-16 window; prefer the one closer to 14
    assert pick_expiration(today=today, available=available) == date(2026, 5, 9)


def test_raises_when_no_expiration_in_window():
    today = date(2026, 4, 25)
    available = [date(2026, 5, 1), date(2026, 5, 22)]  # 6d and 27d
    with pytest.raises(NoSuitableExpirationError):
        pick_expiration(today=today, available=available)


def test_ignores_past_expirations():
    today = date(2026, 4, 25)
    available = [date(2026, 4, 18), date(2026, 5, 8)]  # past, 13d
    assert pick_expiration(today=today, available=available) == date(2026, 5, 8)


def test_raises_on_empty_list():
    with pytest.raises(NoSuitableExpirationError):
        pick_expiration(today=date(2026, 4, 25), available=[])
