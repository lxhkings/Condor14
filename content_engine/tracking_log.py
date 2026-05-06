"""Tracking log for each ticker's setups.

Returns two separate lists:
- active_setups: setups that are still open (not yet reached target_exit_date)
- settled_setups: setups that have been settled (won or lost)
"""

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from ledger.schema import Ledger, Setup


@dataclass(frozen=True)
class ActiveRow:
    """A setup that is still in progress."""
    ticker: str
    open_date: date
    open_price: float
    target_date: date
    days_in: int
    status: str  # "Open (Day X)"


@dataclass(frozen=True)
class SettledRow:
    """A setup that has been settled."""
    ticker: str
    open_date: date
    open_price: float
    settled_date: date
    status: str  # "Won" or "Lost"
    pnl: float


def _setups_for_ticker(ledger: Ledger, ticker: str) -> Iterable[Setup]:
    return (s for s in ledger.setups if s.ticker == ticker)


def build_tracking_log(
    *,
    ticker: str,
    ledger: Ledger,
    today: date,
) -> tuple[list[ActiveRow], list[SettledRow]]:
    """Return (active_setups, settled_setups) for the given ticker.

    Active setups are sorted by open_date descending.
    Settled setups are sorted by settled_date descending.
    """
    active: list[ActiveRow] = []
    settled: list[SettledRow] = []

    for setup in _setups_for_ticker(ledger, ticker):
        if setup.status == "open":
            # Still in progress
            days_in = (today - setup.start_date).days
            active.append(ActiveRow(
                ticker=setup.ticker,
                open_date=setup.start_date,
                open_price=setup.underlying_at_open,
                target_date=setup.target_exit_date,
                days_in=days_in,
                status=f"Open (Day {days_in})",
            ))
        elif setup.settlement is not None:
            # Settled
            settled.append(SettledRow(
                ticker=setup.ticker,
                open_date=setup.start_date,
                open_price=setup.underlying_at_open,
                settled_date=setup.settlement.settled_on,
                status="Won" if setup.status == "won" else "Lost",
                pnl=setup.settlement.final_pnl_per_spread,
            ))

    # Sort: active by open_date desc, settled by settled_date desc
    active.sort(key=lambda r: r.open_date, reverse=True)
    settled.sort(key=lambda r: r.settled_date, reverse=True)

    return active, settled
