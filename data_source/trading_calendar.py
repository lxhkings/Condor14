"""NYSE trading-day guard for the daily pipeline.

Used both as a library function (``is_trading_day``) and as a CLI exit-code
check (``python -m data_source.trading_calendar``) inside GitHub Actions.
"""

import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

_NYSE = mcal.get_calendar("NYSE")


def is_trading_day(d: date) -> bool:
    """Return True if ``d`` is a NYSE full or partial trading day."""
    valid = _NYSE.valid_days(start_date=d, end_date=d)
    return bool(valid.size)


def is_trading_day_now_et() -> bool:
    """Return True if the current US/Eastern date is a NYSE trading day."""
    et_today = datetime.now(ZoneInfo("America/New_York")).date()
    return is_trading_day(et_today)


if __name__ == "__main__":
    sys.exit(0 if is_trading_day_now_et() else 1)
