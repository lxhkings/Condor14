# tests/test_screener.py
from datetime import date

from ledger.schema import Ledger, Setup
from site_builder.screener import build_screener_data


def _settled(ticker, sector, settled_on, pnl, status="won", side=None) -> Setup:
    from ledger.schema import Settlement
    return Setup(
        id=f"{ticker}-{settled_on}", ticker=ticker, sector=sector,
        start_date=date(2026, 1, 1), target_exit_date=settled_on,
        expiry_used=settled_on,
        underlying_at_open=100.0, atr14_at_open=2.0, sma20_at_open=100.0,
        iv_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=105.0, long_call_strike=110.0,
        short_put_strike=95.0,  long_put_strike=90.0,
        net_credit_at_open=1.0, wing_width=5.0,
        max_profit=1.0, max_loss=4.0,
        break_even_upper=106.0, break_even_lower=94.0,
        status=status, daily_marks=[],
        settlement=Settlement(
            settled_on=settled_on, final_underlying=100.0,
            breached_side=side, final_pnl_per_spread=pnl,
        ),
    )


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


def test_top_realized_sorted_by_pnl_desc():
    from site_builder.screener import top_realized_pnl
    ledger = Ledger(setups=[
        _settled("A", "S1", date(2026, 5, 1), 50.0),
        _settled("B", "S1", date(2026, 5, 1), 300.0),
        _settled("C", "S1", date(2026, 5, 1), 100.0),
    ])
    rows = top_realized_pnl(ledger)
    assert [r.ticker for r in rows] == ["B", "C", "A"]
    assert rows[0].realized_pnl == 300.0
    assert rows[0].trades == 1
    assert rows[0].win_rate == 1.0


def test_top_realized_aggregates_per_ticker():
    from site_builder.screener import top_realized_pnl
    ledger = Ledger(setups=[
        _settled("NVDA", "S1", date(2026, 5, 1), 100.0, "won"),
        _settled("NVDA", "S1", date(2026, 5, 2), -40.0, "lost", side="upper"),
    ])
    rows = top_realized_pnl(ledger)
    assert len(rows) == 1
    assert rows[0].ticker == "NVDA"
    assert rows[0].realized_pnl == 60.0
    assert rows[0].trades == 2
    assert rows[0].win_rate == 0.5


def test_top_realized_caps_at_10():
    from site_builder.screener import top_realized_pnl
    ledger = Ledger(setups=[
        _settled(f"T{i}", "S1", date(2026, 5, 1), float(i + 1))
        for i in range(15)
    ])
    rows = top_realized_pnl(ledger)
    assert len(rows) == 10
    # highest pnl first: T14 (15.0) ... down to T5 (6.0)
    assert rows[0].ticker == "T14"


def test_top_realized_empty_ledger():
    from site_builder.screener import top_realized_pnl
    assert top_realized_pnl(Ledger()) == []


def test_build_screener_data_includes_top_realized():
    ledger = Ledger(setups=[
        _settled("NVDA", "S1", date(2026, 5, 1), 100.0),
    ])
    data = build_screener_data(ledger, today=date(2026, 5, 10))
    assert "top_realized" in data
    assert data["top_realized"][0].ticker == "NVDA"
