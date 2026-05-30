# tests/test_leaderboard.py
from datetime import date

from ledger.schema import Ledger, Settlement, Setup
from site_builder.leaderboard import LeaderboardRow, build_leaderboard_data


def _settled(ticker, settled_on, pnl, status="won", side=None) -> Setup:
    from datetime import timedelta
    return Setup(
        id=f"{ticker}-{settled_on}", ticker=ticker, sector="X",
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
            breached_side=side, final_pnl_per_spread=pnl,
        ),
    )


def test_empty_ledger_returns_empty_list():
    rows = build_leaderboard_data(Ledger(), today=date(2026, 5, 10))
    assert rows == []


def test_rows_are_sorted_by_win_rate_desc():
    ledger = Ledger(setups=[
        _settled("AAA", date(2026, 5, 1), 100.0, "won"),
        _settled("AAA", date(2026, 5, 2), 100.0, "won"),
        _settled("BBB", date(2026, 5, 1), -300.0, "lost", side="upper"),
        _settled("BBB", date(2026, 5, 2), 100.0, "won"),
    ])
    rows = build_leaderboard_data(ledger, today=date(2026, 5, 10))
    assert rows[0].ticker == "AAA"
    assert rows[1].ticker == "BBB"
    assert rows[0].win_rate == 1.0
    assert rows[1].win_rate == 0.5


def test_tiebreak_by_setups_tracked_desc():
    ledger = Ledger(setups=[
        _settled("AAA", date(2026, 5, 1), 100.0, "won"),
        _settled("BBB", date(2026, 5, 1), 100.0, "won"),
        _settled("BBB", date(2026, 5, 2), 100.0, "won"),
    ])
    rows = build_leaderboard_data(ledger, today=date(2026, 5, 10))
    # Both 100% win rate; BBB has 2 settled vs AAA's 1
    assert rows[0].ticker == "BBB"
    assert rows[1].ticker == "AAA"


def test_max_drawdown_and_worst_loss_populated():
    ledger = Ledger(setups=[
        _settled("X", date(2026, 5, 1), 100.0, "won"),
        _settled("X", date(2026, 5, 2), -300.0, "lost", side="upper"),
        _settled("X", date(2026, 5, 3), 100.0, "won"),
    ])
    rows = build_leaderboard_data(ledger, today=date(2026, 5, 10))
    assert rows[0].ticker == "X"
    assert rows[0].max_drawdown < 0
    assert rows[0].worst_single_loss == -300.0


def test_last_settlement_is_most_recent():
    from datetime import date
    ledger = Ledger(setups=[
        _settled("X", date(2026, 5, 1), 100.0, "won"),
        _settled("X", date(2026, 5, 5), 100.0, "won"),
        _settled("X", date(2026, 5, 3), 100.0, "won"),
    ])
    rows = build_leaderboard_data(ledger, today=date(2026, 5, 10))
    assert rows[0].last_settlement == date(2026, 5, 5)
