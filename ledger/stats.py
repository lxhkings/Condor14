"""Roll-up statistics over a 30-day window of settled setups.

`max_drawdown` is computed on the running cumulative P&L curve of settled
setups in chronological order: peak-to-trough difference (negative).

`worst_single_loss` is the minimum `final_pnl_per_spread` among lost setups.
"""

from collections import defaultdict
from datetime import date, timedelta

from ledger.schema import Ledger


def _within_window(d: date, today: date, window_days: int) -> bool:
    return today - timedelta(days=window_days) <= d <= today


def _summarize(settled_setups) -> dict:
    settled = sorted(
        [s for s in settled_setups if s.settlement is not None],
        key=lambda s: s.settlement.settled_on,
    )
    if not settled:
        return {
            "sample_size": 0,
            "win_rate": None,
            "worst_single_loss": None,
            "max_drawdown": None,
            "cumulative_pnl": 0.0,
        }
    n = len(settled)
    wins = sum(1 for s in settled if s.status == "won")
    pnls = [s.settlement.final_pnl_per_spread for s in settled]
    losses = [p for p in pnls if p < 0]

    # Cumulative curve and max drawdown
    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        running += p
        peak = max(peak, running)
        max_dd = min(max_dd, running - peak)

    return {
        "sample_size": n,
        "win_rate": wins / n,
        "worst_single_loss": min(losses) if losses else 0.0,
        "max_drawdown": max_dd,
        "cumulative_pnl": running,
    }


def rolling_30day_stats(ledger: Ledger, *, today: date) -> dict:
    in_window = [
        s for s in ledger.setups
        if s.settlement is not None
        and _within_window(s.settlement.settled_on, today, window_days=30)
    ]
    return _summarize(in_window)


def per_ticker_stats(ledger: Ledger, *, today: date) -> dict[str, dict]:
    by_ticker: dict[str, list] = defaultdict(list)
    for s in ledger.setups:
        if s.settlement is None:
            continue
        if not _within_window(s.settlement.settled_on, today, window_days=30):
            continue
        by_ticker[s.ticker].append(s)
    return {ticker: _summarize(setups) for ticker, setups in by_ticker.items()}


def per_ticker_alltime_stats(ledger: Ledger) -> dict[str, dict]:
    """Per-ticker summary over ALL settled setups (no time window).

    Distinct from per_ticker_stats, which restricts to a 30-day window for the
    Mode B leaderboard. This un-windowed view powers the evergreen Mode A
    Top Realized P&L board.
    """
    by_ticker: dict[str, list] = defaultdict(list)
    for s in ledger.setups:
        if s.settlement is None:
            continue
        by_ticker[s.ticker].append(s)
    return {ticker: _summarize(setups) for ticker, setups in by_ticker.items()}
