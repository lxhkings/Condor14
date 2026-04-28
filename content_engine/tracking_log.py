"""Weekly tracking-log row builder per spec §5.4.

For a given ticker and ``today`` ET, produce one row per Friday in the past
``weeks * 7`` days. Each row reflects either a settlement that occurred during
that week or the open status of an in-flight setup whose lifecycle includes
that Friday. Rows are returned newest-first.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from ledger.schema import Ledger, Setup


@dataclass(frozen=True)
class TrackingRow:
    week_ending: date
    open_price: float
    status_label: str
    note: str


def _friday_of_week_containing(d: date) -> date:
    """Friday of the ISO week that contains *d* (Monday-based week)."""
    # Monday=0, Friday=4
    weekday = d.weekday()
    if weekday <= 4:
        return d + timedelta(days=4 - weekday)
    # Saturday or Sunday: next Friday
    return d + timedelta(days=(11 - weekday))


def _setups_for_ticker(ledger: Ledger, ticker: str) -> Iterable[Setup]:
    return (s for s in ledger.setups if s.ticker == ticker)


def _row_for_settled(setup: Setup) -> TrackingRow:
    fri = _friday_of_week_containing(setup.settlement.settled_on)
    label = "Won (Day 14)" if setup.status == "won" else "Lost (Day 14)"
    if setup.status == "lost":
        side = setup.settlement.breached_side or "boundary"
        note = f"Closed at ${setup.settlement.final_underlying:.2f} — {side} breach"
    else:
        note = f"Closed at ${setup.settlement.final_underlying:.2f} — within range"
    return TrackingRow(
        week_ending=fri,
        open_price=setup.underlying_at_open,
        status_label=label,
        note=note,
    )


def _row_for_open(setup: Setup, fri: date) -> TrackingRow:
    days_into = (fri - setup.start_date).days
    return TrackingRow(
        week_ending=fri,
        open_price=setup.underlying_at_open,
        status_label=f"Open (Day {days_into})",
        note="In-flight, hold-to-expiration",
    )


def build_tracking_log(
    *,
    ticker: str,
    ledger: Ledger,
    today: date,
    weeks: int = 12,
) -> list[TrackingRow]:
    cutoff = today - timedelta(days=weeks * 7)
    today_fri = _friday_of_week_containing(today)
    rows_by_friday: dict[date, TrackingRow] = {}

    for setup in _setups_for_ticker(ledger, ticker):
        if setup.settlement is not None:
            fri = _friday_of_week_containing(setup.settlement.settled_on)
            if cutoff <= fri <= today:
                rows_by_friday[fri] = _row_for_settled(setup)
        elif setup.status == "open":
            cur = _friday_of_week_containing(setup.start_date)
            end = _friday_of_week_containing(setup.target_exit_date)
            while cur <= end:
                if cutoff <= cur <= today_fri and cur not in rows_by_friday:
                    rows_by_friday[cur] = _row_for_open(setup, cur)
                cur = cur + timedelta(days=7)

    return sorted(rows_by_friday.values(), key=lambda r: r.week_ending, reverse=True)[:weeks]
