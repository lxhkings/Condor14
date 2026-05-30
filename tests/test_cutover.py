# tests/test_cutover.py
from datetime import date, timedelta

from ledger.schema import Ledger, Settlement, Setup
from site_builder.leaderboard import cutover_satisfied


def _settled_setup(settled_on: date, status: str = "won") -> Setup:
    return Setup(
        id=f"X-{settled_on}", ticker="X", sector="X",
        start_date=settled_on - timedelta(days=14), target_exit_date=settled_on,
        expiry_used=settled_on,
        underlying_at_open=100.0, atr14_at_open=2.0, sma20_at_open=100.0,
        vol_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=105.0, long_call_strike=110.0,
        short_put_strike=95.0,  long_put_strike=90.0,
        net_credit_at_open=1.0, wing_width=5.0,
        max_profit=1.0, max_loss=4.0,
        break_even_upper=106.0, break_even_lower=94.0,
        status=status, daily_marks=[],
        settlement=Settlement(
            settled_on=settled_on, final_underlying=100.0,
            breached_side=None, final_pnl_per_spread=100.0,
        ),
    )


def test_cutover_false_when_under_200_settled():
    ledger = Ledger(
        setups=[_settled_setup(date(2026, 1, 15)) for _ in range(199)],
        first_settlement_date=date(2026, 1, 15),
    )
    assert cutover_satisfied(ledger, today=date(2026, 5, 1)) is False


def test_cutover_false_when_under_30_days_since_first():
    ledger = Ledger(
        setups=[_settled_setup(date(2026, 4, 1)) for _ in range(250)],
        first_settlement_date=date(2026, 4, 1),
    )
    assert cutover_satisfied(ledger, today=date(2026, 4, 30)) is False


def test_cutover_true_when_both_satisfied():
    ledger = Ledger(
        setups=[_settled_setup(date(2026, 4, 1)) for _ in range(250)],
        first_settlement_date=date(2026, 4, 1),
    )
    assert cutover_satisfied(ledger, today=date(2026, 5, 1)) is True


def test_cutover_false_when_first_settlement_date_is_none():
    ledger = Ledger(
        setups=[_settled_setup(date(2026, 4, 1)) for _ in range(250)],
        first_settlement_date=None,
    )
    assert cutover_satisfied(ledger, today=date(2026, 6, 1)) is False


def test_cutover_excludes_open_setups_from_count():
    settled = [_settled_setup(date(2026, 4, 1)) for _ in range(199)]
    open_one = Setup(
        id="OPEN", ticker="X", sector="X",
        start_date=date(2026, 4, 1), target_exit_date=date(2026, 4, 15),
        expiry_used=date(2026, 4, 15),
        underlying_at_open=100.0, atr14_at_open=2.0, sma20_at_open=100.0,
        vol_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=105.0, long_call_strike=110.0,
        short_put_strike=95.0,  long_put_strike=90.0,
        net_credit_at_open=1.0, wing_width=5.0,
        max_profit=1.0, max_loss=4.0,
        break_even_upper=106.0, break_even_lower=94.0,
        status="open", daily_marks=[], settlement=None,
    )
    ledger = Ledger(setups=settled + [open_one], first_settlement_date=date(2026, 4, 1))
    # 199 settled + 1 open = 200 total but only 199 settled → False
    assert cutover_satisfied(ledger, today=date(2026, 6, 1)) is False
