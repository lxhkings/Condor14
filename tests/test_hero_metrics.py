"""Tests for site_builder.hero.compute_hero_metrics."""

from datetime import date

from ledger.schema import Ledger, Setup, Settlement
from site_builder.hero import compute_hero_metrics


def _make_setup(
    ticker: str,
    status: str,
    start: date,
    settled_on: date | None = None,
    uid: str | None = None,
) -> Setup:
    settlement = (
        Settlement(
            settled_on=settled_on,
            final_underlying=100.0,
            breached_side=None,
            final_pnl_per_spread=2.0 if status == "won" else -3.0,
        )
        if settled_on is not None
        else None
    )
    return Setup(
        id=uid or f"{ticker}-{start}",
        ticker=ticker,
        sector="Mega-Cap Tech",
        start_date=start,
        target_exit_date=date(2026, 5, 15),
        expiry_used=date(2026, 5, 15),
        underlying_at_open=100.0,
        atr14_at_open=2.0,
        sma20_at_open=99.0,
        iv_percentile_at_open=50,
        trend_bias="neutral",
        short_call_strike=105.0,
        long_call_strike=110.0,
        short_put_strike=95.0,
        long_put_strike=90.0,
        net_credit_at_open=2.0,
        wing_width=5.0,
        max_profit=2.0,
        max_loss=3.0,
        break_even_upper=107.0,
        break_even_lower=93.0,
        status=status,
        daily_marks=[],
        settlement=settlement,
    )


def test_empty_ledger_zero_metrics():
    ledger = Ledger(
        setups=[],
        skipped=[],
        site_launch_date=None,
        first_settlement_date=None,
    )
    m = compute_hero_metrics(ledger, today=date(2026, 5, 1))
    assert m["days_running"] == 0
    assert m["setups_tracked"] == 0
    assert m["settled_count"] == 0
    assert m["progress_pct"] == 0
    assert m["progress_label"] == "0 / 200"
    assert m["cutover_reached"] is False


def test_partial_progress():
    setups = [
        _make_setup("AAPL", "won", date(2026, 4, 1), date(2026, 4, 15)),
        _make_setup("MSFT", "lost", date(2026, 4, 2), date(2026, 4, 16)),
        _make_setup("NVDA", "open", date(2026, 4, 3)),
    ]
    ledger = Ledger(
        setups=setups,
        skipped=[],
        site_launch_date=date(2026, 4, 1),
        first_settlement_date=date(2026, 4, 15),
    )
    m = compute_hero_metrics(ledger, today=date(2026, 5, 1))
    assert m["days_running"] == 30
    assert m["setups_tracked"] == 3
    assert m["settled_count"] == 2
    assert m["progress_pct"] == 1  # 2 * 100 // 200 = 1
    assert m["progress_label"] == "2 / 200"
    assert m["cutover_reached"] is False


def test_cutover_reached_clamps_progress():
    setups = [
        _make_setup(f"T{i}", "won", date(2026, 1, 1), date(2026, 1, 15), uid=f"T{i}-0")
        for i in range(250)
    ]
    ledger = Ledger(
        setups=setups,
        skipped=[],
        site_launch_date=date(2026, 1, 1),
        first_settlement_date=date(2026, 1, 15),
    )
    m = compute_hero_metrics(ledger, today=date(2026, 5, 1))
    assert m["settled_count"] == 250
    assert m["progress_pct"] == 100  # clamped
    assert m["cutover_reached"] is True
