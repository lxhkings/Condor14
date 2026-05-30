# tests/test_tracking_log.py
from datetime import date

import pytest

from content_engine.tracking_log import ActiveRow, SettledRow, build_tracking_log
from ledger.schema import Ledger, Settlement, Setup


def _setup(ticker, start, target_exit, *, status="open", final_underlying=None,
           pnl=None, side=None) -> Setup:
    settlement = None
    if status in ("won", "lost"):
        settlement = Settlement(
            settled_on=target_exit,
            final_underlying=final_underlying,
            breached_side=side,
            final_pnl_per_spread=pnl,
        )
    return Setup(
        id=f"{ticker}-{start}", ticker=ticker, sector="X",
        start_date=start, target_exit_date=target_exit, expiry_used=target_exit,
        underlying_at_open=200.0, atr14_at_open=4.0, sma20_at_open=200.0,
        vol_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=210.0, long_call_strike=215.0,
        short_put_strike=190.0, long_put_strike=185.0,
        net_credit_at_open=1.5, wing_width=5.0,
        max_profit=1.5, max_loss=3.5,
        break_even_upper=211.5, break_even_lower=188.5,
        status=status, daily_marks=[], settlement=settlement,
    )


def test_empty_ledger_returns_empty_lists():
    active, settled = build_tracking_log(ticker="NVDA", ledger=Ledger(), today=date(2026, 5, 1))
    assert active == []
    assert settled == []


def test_open_setup_in_active_list():
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 5, 1), date(2026, 5, 15), status="open"),
    ])
    active, settled = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 6))
    assert len(active) == 1
    assert len(settled) == 0
    assert active[0].open_date == date(2026, 5, 1)
    assert active[0].open_price == 200.0
    assert active[0].target_date == date(2026, 5, 15)
    assert active[0].days_in == 5
    assert active[0].status == "Open (Day 5)"


def test_settled_setup_in_settled_list():
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 4, 28), date(2026, 5, 12), status="won",
               final_underlying=205.0, pnl=150.0, side=None),
    ])
    active, settled = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 16))
    assert len(active) == 0
    assert len(settled) == 1
    assert settled[0].open_date == date(2026, 4, 28)
    assert settled[0].settled_date == date(2026, 5, 12)
    assert settled[0].status == "Won"
    assert settled[0].pnl == 150.0


def test_lost_setup_shows_status():
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 5, 1), date(2026, 5, 15), status="lost",
               final_underlying=170.0, pnl=-350.0, side="lower"),
    ])
    active, settled = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 16))
    assert settled[0].status == "Lost"
    assert settled[0].pnl == -350.0


def test_multiple_setups_sorted_correctly():
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 5, 5), date(2026, 5, 19), status="open"),
        _setup("NVDA", date(2026, 5, 1), date(2026, 5, 15), status="open"),
        _setup("NVDA", date(2026, 4, 28), date(2026, 5, 12), status="won",
               final_underlying=205.0, pnl=150.0, side=None),
        _setup("NVDA", date(2026, 4, 25), date(2026, 5, 9), status="lost",
               final_underlying=170.0, pnl=-350.0, side="lower"),
    ])
    active, settled = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 6))

    # Active sorted by open_date desc
    assert len(active) == 2
    assert active[0].open_date == date(2026, 5, 5)
    assert active[1].open_date == date(2026, 5, 1)

    # Settled sorted by settled_date desc
    assert len(settled) == 2
    assert settled[0].settled_date == date(2026, 5, 12)
    assert settled[1].settled_date == date(2026, 5, 9)


def test_other_ticker_setups_filtered_out():
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 4, 28), date(2026, 5, 12), status="won",
               final_underlying=205.0, pnl=150.0, side=None),
        _setup("TSLA", date(2026, 4, 28), date(2026, 5, 12), status="won",
               final_underlying=205.0, pnl=150.0, side=None),
    ])
    active, settled = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 16))
    assert len(settled) == 1
    assert settled[0].ticker == "NVDA"
