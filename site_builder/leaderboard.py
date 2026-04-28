# stock/site_builder/leaderboard.py
"""Cutover gate (this file) and leaderboard data assembly (added in Task 10).

Per spec §7.1: Mode B (Live Performance Tracker) unlocks only when both:
    - settled_count >= 200
    - days_since_first_settlement >= 30
"""

from dataclasses import dataclass
from datetime import date

from ledger.schema import Ledger
from ledger.stats import per_ticker_stats


def cutover_satisfied(ledger: Ledger, *, today: date) -> bool:
    settled = [s for s in ledger.setups if s.status in ("won", "lost")]
    if len(settled) < 200:
        return False
    if ledger.first_settlement_date is None:
        return False
    return (today - ledger.first_settlement_date).days >= 30


@dataclass(frozen=True)
class LeaderboardRow:
    ticker: str
    win_rate: float
    setups_tracked: int
    max_drawdown: float
    worst_single_loss: float
    last_settlement: date | None


def build_leaderboard_data(ledger: Ledger, *, today: date) -> list[LeaderboardRow]:
    per_ticker = per_ticker_stats(ledger, today=today)
    rows: list[LeaderboardRow] = []
    for ticker, stats in per_ticker.items():
        if stats["sample_size"] == 0:
            continue
        last = max(
            (s.settlement.settled_on for s in ledger.setups
             if s.ticker == ticker and s.settlement is not None),
            default=None,
        )
        rows.append(LeaderboardRow(
            ticker=ticker,
            win_rate=stats["win_rate"] or 0.0,
            setups_tracked=stats["sample_size"],
            max_drawdown=stats["max_drawdown"] or 0.0,
            worst_single_loss=stats["worst_single_loss"] or 0.0,
            last_settlement=last,
        ))
    rows.sort(key=lambda r: (-r.win_rate, -r.setups_tracked, r.ticker))
    return rows
