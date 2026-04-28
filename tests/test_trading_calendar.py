from datetime import date
from data_source.trading_calendar import is_trading_day


def test_normal_weekday_is_trading_day():
    # Wed 2025-04-30 — normal trading day
    assert is_trading_day(date(2025, 4, 30)) is True


def test_saturday_is_not_trading_day():
    assert is_trading_day(date(2025, 5, 3)) is False


def test_sunday_is_not_trading_day():
    assert is_trading_day(date(2025, 5, 4)) is False


def test_christmas_is_not_trading_day():
    # Christmas 2025, Thursday — full close
    assert is_trading_day(date(2025, 12, 25)) is False


def test_july_4_is_not_trading_day():
    # July 4 2025, Friday — full close
    assert is_trading_day(date(2025, 7, 4)) is False


def test_thanksgiving_is_not_trading_day():
    # Thanksgiving 2025, Thu Nov 27
    assert is_trading_day(date(2025, 11, 27)) is False
