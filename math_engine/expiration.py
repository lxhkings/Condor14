"""Pick the option expiration in the 13-16 day target window.

The MVP rule: prefer expirations 13-16 calendar days from today. Among
qualifying expirations, pick the one whose distance from 14 days is smallest.
If multiple share the same distance, pick the earlier date.

If no expiration falls inside the window, raise. (The pipeline catches this
and skips the ticker for the day.)
"""

from datetime import date
from typing import Sequence


class NoSuitableExpirationError(Exception):
    """No expiration within the 13-16 day window."""


def pick_expiration(*, today: date, available: Sequence[date]) -> date:
    candidates = []
    for exp in available:
        days = (exp - today).days
        if 13 <= days <= 16:
            candidates.append((abs(days - 14), days, exp))

    if not candidates:
        raise NoSuitableExpirationError(
            f"no expiration in 13-16 day window from {today}"
        )

    # Sort by (distance_from_14, days, date) so earliest tie-breaker wins.
    candidates.sort()
    return candidates[0][2]
