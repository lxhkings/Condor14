from datetime import date

import pytest

from ledger.schema import Ledger, Settlement, Setup
from ledger.stats import per_ticker_stats, rolling_30day_stats


def _settled(ticker, settled_on, pnl, status="won", side=None) -> Setup:
    """Helper: produce a settled Setup with only the fields stats use."""
    return Setup(
        id=f"{ticker}-{settled_on}", ticker=ticker, sector="X",
        start_date=date(2026, 1, 1), target_exit_date=settled_on,
        expiry_used=settled_on,
        underlying_at_open=100.0, atr14_at_open=1.0, sma20_at_open=100.0,
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


def test_rolling_30day_stats_excludes_open_setups():
    ledger = Ledger(setups=[
        _settled("NVDA", date(2026, 5, 5), 100.0, "won"),
    ])
    # Inject an open setup
    ledger.setups.append(
        Setup(
            id="OPEN", ticker="NVDA", sector="X",
            start_date=date(2026, 5, 1), target_exit_date=date(2026, 5, 15),
            expiry_used=date(2026, 5, 15),
            underlying_at_open=100.0, atr14_at_open=1.0, sma20_at_open=100.0,
            vol_percentile_at_open=50, trend_bias="neutral",
            short_call_strike=105.0, long_call_strike=110.0,
            short_put_strike=95.0,  long_put_strike=90.0,
            net_credit_at_open=1.0, wing_width=5.0,
            max_profit=1.0, max_loss=4.0,
            break_even_upper=106.0, break_even_lower=94.0,
            status="open", daily_marks=[], settlement=None,
        )
    )
    s = rolling_30day_stats(ledger, today=date(2026, 5, 10))
    assert s["sample_size"] == 1
    assert s["win_rate"] == pytest.approx(1.0)


def test_rolling_window_excludes_old_settlements():
    ledger = Ledger(setups=[
        _settled("NVDA", date(2026, 3, 1),  100.0, "won"),    # 70 days ago
        _settled("NVDA", date(2026, 5, 1),  100.0, "won"),    # 9 days ago
        _settled("NVDA", date(2026, 4, 25), -300.0, "lost",
                 side="upper"),                                  # 15 days ago
    ])
    s = rolling_30day_stats(ledger, today=date(2026, 5, 10))
    assert s["sample_size"] == 2
    assert s["win_rate"] == pytest.approx(0.5)
    assert s["worst_single_loss"] == pytest.approx(-300.0)


def test_max_drawdown_running_total():
    # Equity curve: +100, -300, +100, +100, -300 -> running totals
    # 100, -200, -100, 0, -300. peak=100, lowest after peak=-300, dd=400.
    ledger = Ledger(setups=[
        _settled("X", date(2026, 5, 1), 100.0, "won"),
        _settled("X", date(2026, 5, 2), -300.0, "lost", side="upper"),
        _settled("X", date(2026, 5, 3), 100.0, "won"),
        _settled("X", date(2026, 5, 4), 100.0, "won"),
        _settled("X", date(2026, 5, 5), -300.0, "lost", side="lower"),
    ])
    s = rolling_30day_stats(ledger, today=date(2026, 5, 10))
    assert s["max_drawdown"] == pytest.approx(-400.0)


def test_per_ticker_stats_groups_correctly():
    ledger = Ledger(setups=[
        _settled("NVDA", date(2026, 5, 1), 100.0, "won"),
        _settled("NVDA", date(2026, 5, 2), 100.0, "won"),
        _settled("TSLA", date(2026, 5, 1), -300.0, "lost", side="upper"),
    ])
    s = per_ticker_stats(ledger, today=date(2026, 5, 10))
    assert s["NVDA"]["sample_size"] == 2
    assert s["NVDA"]["win_rate"] == pytest.approx(1.0)
    assert s["TSLA"]["win_rate"] == pytest.approx(0.0)
    assert s["TSLA"]["worst_single_loss"] == pytest.approx(-300.0)


def test_empty_ledger_returns_zero_sample():
    s = rolling_30day_stats(Ledger(), today=date(2026, 5, 10))
    assert s["sample_size"] == 0
    assert s["win_rate"] is None


def test_per_ticker_alltime_includes_old_settlements():
    from ledger.stats import per_ticker_alltime_stats
    ledger = Ledger(setups=[
        _settled("NVDA", date(2026, 1, 1), 100.0, "won"),      # >30 days old
        _settled("NVDA", date(2026, 5, 1), 100.0, "won"),
        _settled("TSLA", date(2026, 4, 25), -300.0, "lost", side="upper"),
    ])
    s = per_ticker_alltime_stats(ledger)
    assert s["NVDA"]["sample_size"] == 2
    assert s["NVDA"]["cumulative_pnl"] == pytest.approx(200.0)
    assert s["NVDA"]["win_rate"] == pytest.approx(1.0)
    assert s["TSLA"]["sample_size"] == 1
    assert s["TSLA"]["cumulative_pnl"] == pytest.approx(-300.0)


def test_per_ticker_alltime_excludes_open_setups():
    from ledger.stats import per_ticker_alltime_stats
    ledger = Ledger(setups=[
        _settled("NVDA", date(2026, 5, 1), 100.0, "won"),
    ])
    ledger.setups.append(Setup(
        id="OPEN", ticker="NVDA", sector="X",
        start_date=date(2026, 5, 1), target_exit_date=date(2026, 5, 15),
        expiry_used=date(2026, 5, 15),
        underlying_at_open=100.0, atr14_at_open=1.0, sma20_at_open=100.0,
        vol_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=105.0, long_call_strike=110.0,
        short_put_strike=95.0,  long_put_strike=90.0,
        net_credit_at_open=1.0, wing_width=5.0,
        max_profit=1.0, max_loss=4.0,
        break_even_upper=106.0, break_even_lower=94.0,
        status="open", daily_marks=[], settlement=None,
    ))
    s = per_ticker_alltime_stats(ledger)
    assert s["NVDA"]["sample_size"] == 1


def test_per_ticker_alltime_empty_ledger():
    from ledger.stats import per_ticker_alltime_stats
    assert per_ticker_alltime_stats(Ledger()) == {}
