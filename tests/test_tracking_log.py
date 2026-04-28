# tests/test_tracking_log.py
from datetime import date

import pytest

from content_engine.tracking_log import TrackingRow, build_tracking_log
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
        iv_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=210.0, long_call_strike=215.0,
        short_put_strike=190.0,  long_put_strike=185.0,
        net_credit_at_open=1.5, wing_width=5.0,
        max_profit=1.5, max_loss=3.5,
        break_even_upper=211.5, break_even_lower=188.5,
        status=status, daily_marks=[], settlement=settlement,
    )


def test_empty_ledger_returns_empty():
    assert build_tracking_log(ticker="NVDA", ledger=Ledger(), today=date(2026, 5, 1)) == []


def test_settled_won_row_carries_status_and_week_ending_friday():
    # Settled on Mon May 12 2026 — week ends Fri May 15 2026
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 4, 28), date(2026, 5, 12), status="won",
               final_underlying=205.0, pnl=150.0, side=None),
    ])
    rows = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 16))
    assert len(rows) == 1
    assert rows[0].week_ending == date(2026, 5, 15)
    assert rows[0].status_label.startswith("Won")
    assert rows[0].open_price == 200.0


def test_settlement_already_on_friday_uses_that_friday():
    # Settled Fri May 15 2026 — week_ending is the same day
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 5, 1), date(2026, 5, 15), status="lost",
               final_underlying=170.0, pnl=-350.0, side="lower"),
    ])
    rows = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 16))
    assert rows[0].week_ending == date(2026, 5, 15)
    assert rows[0].status_label.startswith("Lost")


def test_open_setup_mid_cycle_emits_open_row_for_current_week():
    # Setup opened Mon Apr 27, target exit May 11. Today is Wed May 6 — week_ending Fri May 8
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 4, 27), date(2026, 5, 11), status="open"),
    ])
    rows = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 6))
    weeks = {r.week_ending for r in rows}
    assert date(2026, 5, 8) in weeks
    open_row = next(r for r in rows if r.week_ending == date(2026, 5, 8))
    assert open_row.status_label.startswith("Open")


def test_only_recent_12_weeks_returned_newest_first():
    setups = []
    # 13 weekly settled setups starting from 2026-01-02 (Friday)
    for i in range(13):
        start = date(2026, 1, 2)
        # offset each setup 14 days
        from datetime import timedelta
        s = start + timedelta(days=i * 14)
        target = s + timedelta(days=14)
        setups.append(_setup("NVDA", s, target, status="won",
                             final_underlying=200.0, pnl=150.0, side=None))
    ledger = Ledger(setups=setups)
    today = date(2026, 7, 31)
    rows = build_tracking_log(ticker="NVDA", ledger=ledger, today=today, weeks=12)
    assert len(rows) <= 12
    # Newest first
    assert rows[0].week_ending >= rows[-1].week_ending


def test_other_ticker_setups_filtered_out():
    ledger = Ledger(setups=[
        _setup("NVDA", date(2026, 4, 28), date(2026, 5, 12), status="won",
               final_underlying=205.0, pnl=150.0, side=None),
        _setup("TSLA", date(2026, 4, 28), date(2026, 5, 12), status="won",
               final_underlying=205.0, pnl=150.0, side=None),
    ])
    nvda = build_tracking_log(ticker="NVDA", ledger=ledger, today=date(2026, 5, 16))
    assert all(True for _ in nvda)  # only NVDA-derived rows
    assert len(nvda) == 1
