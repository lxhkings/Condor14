# tests/test_screener.py
from datetime import date

from ledger.schema import Ledger, Setup
from site_builder.screener import build_screener_data


def _setup(ticker, sector, start, *, net_credit=1.0, max_loss=4.0, iv=50,
           trend="neutral", underlying=100.0) -> Setup:
    return Setup(
        id=f"{ticker}-{start}", ticker=ticker, sector=sector,
        start_date=start, target_exit_date=start, expiry_used=start,
        underlying_at_open=underlying, atr14_at_open=2.0, sma20_at_open=100.0,
        iv_percentile_at_open=iv, trend_bias=trend,
        short_call_strike=105.0, long_call_strike=110.0,
        short_put_strike=95.0,  long_put_strike=90.0,
        net_credit_at_open=net_credit, wing_width=5.0,
        max_profit=net_credit, max_loss=max_loss,
        break_even_upper=106.0, break_even_lower=94.0,
        status="open", daily_marks=[], settlement=None,
    )


def test_empty_ledger_panels_all_empty():
    data = build_screener_data(Ledger(), today=date(2026, 4, 28))
    assert data["highest_premium_setups"] == []
    assert data["sector_heatmap"] == []
    assert data["newest_setups"] == []


def test_highest_premium_sorted_by_credit_to_loss_ratio_desc():
    ledger = Ledger(setups=[
        _setup("A", "S1", date(2026, 4, 28), net_credit=1.0, max_loss=4.0),  # ratio 0.25
        _setup("B", "S1", date(2026, 4, 28), net_credit=2.0, max_loss=4.0),  # ratio 0.50
        _setup("C", "S1", date(2026, 4, 28), net_credit=0.5, max_loss=4.0),  # ratio 0.125
    ])
    data = build_screener_data(ledger, today=date(2026, 4, 28))
    tickers = [s.ticker for s in data["highest_premium_setups"]]
    assert tickers == ["B", "A", "C"]


def test_highest_premium_caps_at_top_10():
    ledger = Ledger(setups=[
        _setup(f"T{i}", "S1", date(2026, 4, 28), net_credit=float(i+1), max_loss=4.0)
        for i in range(15)
    ])
    data = build_screener_data(ledger, today=date(2026, 4, 28))
    assert len(data["highest_premium_setups"]) == 10


def test_sector_heatmap_aggregates_correctly():
    ledger = Ledger(setups=[
        _setup("A", "Tech", date(2026, 4, 28), iv=80),
        _setup("B", "Tech", date(2026, 4, 28), iv=60),
        _setup("C", "Chips", date(2026, 4, 28), iv=40),
    ])
    data = build_screener_data(ledger, today=date(2026, 4, 28))
    sectors = {h["sector"]: h for h in data["sector_heatmap"]}
    assert sectors["Tech"]["count_open"] == 2
    assert sectors["Tech"]["avg_iv_percentile"] == 70  # (80+60)/2
    assert sectors["Chips"]["count_open"] == 1


def test_newest_setups_filters_by_today():
    ledger = Ledger(setups=[
        _setup("A", "S1", date(2026, 4, 28)),
        _setup("B", "S1", date(2026, 4, 27)),
    ])
    data = build_screener_data(ledger, today=date(2026, 4, 28))
    tickers = {s.ticker for s in data["newest_setups"]}
    assert tickers == {"A"}


def test_days_since_launch_is_positive_after_launch():
    ledger = Ledger(setups=[], site_launch_date=date(2026, 4, 1))
    data = build_screener_data(ledger, today=date(2026, 4, 10))
    assert data["days_since_launch"] == 9
    assert data["site_launch_date"] == date(2026, 4, 1)


def test_days_since_launch_zero_when_today_equals_launch():
    ledger = Ledger(setups=[], site_launch_date=date(2026, 4, 28))
    data = build_screener_data(ledger, today=date(2026, 4, 28))
    assert data["days_since_launch"] == 0


def test_screener_works_when_site_launch_date_is_none():
    ledger = Ledger(setups=[])
    data = build_screener_data(ledger, today=date(2026, 4, 28))
    assert data["site_launch_date"] is None
    assert data["days_since_launch"] == 0
