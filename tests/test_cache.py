from datetime import date

import pytest

from data_source.cache import BarRow, DailyBarsCache, ExpirationsCache


@pytest.fixture
def cache(tmp_path):
    return DailyBarsCache(tmp_path / "cache.sqlite")


def test_upsert_and_read_single_row(cache):
    row = BarRow(
        ticker="NVDA", bar_date=date(2025, 4, 28),
        open=210.0, high=218.0, low=209.0, close=216.61, volume=50_000_000,
    )
    cache.upsert([row])
    out = cache.read("NVDA", start=date(2025, 4, 28), end=date(2025, 4, 28))
    assert out == [row]


def test_read_orders_by_date_ascending(cache):
    rows = [
        BarRow("NVDA", date(2025, 4, 28), 210.0, 218.0, 209.0, 216.6, 1),
        BarRow("NVDA", date(2025, 4, 25), 205.0, 212.0, 204.0, 210.0, 1),
        BarRow("NVDA", date(2025, 4, 27), 209.0, 215.0, 208.0, 213.0, 1),
    ]
    cache.upsert(rows)
    out = cache.read("NVDA", start=date(2025, 4, 25), end=date(2025, 4, 28))
    assert [r.bar_date for r in out] == [
        date(2025, 4, 25), date(2025, 4, 27), date(2025, 4, 28),
    ]


def test_upsert_replaces_existing_row(cache):
    first = BarRow("NVDA", date(2025, 4, 28), 1, 1, 1, 1, 1)
    second = BarRow("NVDA", date(2025, 4, 28), 210.0, 218.0, 209.0, 216.61, 50_000_000)
    cache.upsert([first])
    cache.upsert([second])
    out = cache.read("NVDA", start=date(2025, 4, 28), end=date(2025, 4, 28))
    assert out == [second]


def test_read_filters_by_ticker(cache):
    cache.upsert([
        BarRow("NVDA", date(2025, 4, 28), 1, 2, 0.5, 1.5, 1),
        BarRow("TSLA", date(2025, 4, 28), 100, 110, 95, 105, 1),
    ])
    nvda = cache.read("NVDA", start=date(2025, 4, 28), end=date(2025, 4, 28))
    assert len(nvda) == 1 and nvda[0].ticker == "NVDA"


def test_read_empty_returns_empty_list(cache):
    assert cache.read("NVDA", start=date(2025, 4, 28), end=date(2025, 4, 28)) == []


def test_latest_date_returns_none_when_empty(cache):
    assert cache.latest_date("NVDA") is None


def test_latest_date_returns_max_date(cache):
    cache.upsert([
        BarRow("NVDA", date(2025, 4, 25), 1, 1, 1, 1, 1),
        BarRow("NVDA", date(2025, 4, 28), 1, 1, 1, 1, 1),
        BarRow("NVDA", date(2025, 4, 26), 1, 1, 1, 1, 1),
    ])
    assert cache.latest_date("NVDA") == date(2025, 4, 28)


@pytest.fixture
def exp_cache(tmp_path):
    return ExpirationsCache(tmp_path / "cache.sqlite")


def test_get_returns_none_when_not_cached(exp_cache):
    assert exp_cache.get("AAPL", fetched_on=date(2026, 5, 9)) is None


def test_put_then_get_roundtrip(exp_cache):
    exps = [date(2026, 5, 23), date(2026, 5, 30), date(2026, 6, 20)]
    exp_cache.put("AAPL", fetched_on=date(2026, 5, 9), expirations=exps)
    assert exp_cache.get("AAPL", fetched_on=date(2026, 5, 9)) == exps


def test_get_misses_for_different_date(exp_cache):
    exp_cache.put("AAPL", fetched_on=date(2026, 5, 9),
                  expirations=[date(2026, 5, 23)])
    assert exp_cache.get("AAPL", fetched_on=date(2026, 5, 10)) is None


def test_put_empty_list_is_no_op(exp_cache):
    exp_cache.put("AAPL", fetched_on=date(2026, 5, 9), expirations=[])
    assert exp_cache.get("AAPL", fetched_on=date(2026, 5, 9)) is None


def test_put_idempotent_replaces_existing(exp_cache):
    exp_cache.put("AAPL", fetched_on=date(2026, 5, 9),
                  expirations=[date(2026, 5, 23)])
    exp_cache.put("AAPL", fetched_on=date(2026, 5, 9),
                  expirations=[date(2026, 5, 23), date(2026, 5, 30)])
    assert exp_cache.get("AAPL", fetched_on=date(2026, 5, 9)) == [
        date(2026, 5, 23), date(2026, 5, 30),
    ]


def test_coexists_with_daily_bars_in_same_db(tmp_path):
    p = tmp_path / "cache.sqlite"
    bars = DailyBarsCache(p)
    exps = ExpirationsCache(p)
    bars.upsert([BarRow("AAPL", date(2026, 5, 8), 1.0, 2.0, 0.5, 1.5, 100)])
    exps.put("AAPL", fetched_on=date(2026, 5, 9), expirations=[date(2026, 5, 23)])
    assert bars.read("AAPL", start=date(2026, 5, 8), end=date(2026, 5, 8))
    assert exps.get("AAPL", fetched_on=date(2026, 5, 9)) == [date(2026, 5, 23)]
