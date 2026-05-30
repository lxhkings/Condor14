"""Realized (historical) volatility and its trailing percentile.

Pure functions, no I/O. Used to bucket spintax prose by a *real* volatility
reading instead of a hardcoded placeholder. This is realized (backward-looking)
volatility — page copy must say "realized", not "implied".
"""

import math
from typing import Sequence

TRADING_DAYS_PER_YEAR = 252
MIN_RANK_SAMPLE = 30  # minimum rolling-vol observations before ranking is meaningful


def realized_vol(closes: Sequence[float], window: int = 20) -> float:
    """Annualized realized volatility over the last `window` daily closes.

    = sample stdev of the last `window` daily log returns * sqrt(252).
    Requires at least `window + 1` closes (to form `window` returns).
    """
    if len(closes) < window + 1:
        raise ValueError(
            f"realized_vol needs at least {window + 1} closes, got {len(closes)}"
        )
    rets = [
        math.log(closes[i] / closes[i - 1])
        for i in range(len(closes) - window, len(closes))
    ]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(TRADING_DAYS_PER_YEAR)


def vol_percentile(
    closes: Sequence[float], window: int = 20, lookback: int = 252
) -> int:
    """Percentile rank (0-100) of the latest realized vol vs its trailing
    distribution over `lookback` trading days.

    Builds the rolling `realized_vol` series across the trailing window and
    ranks the most recent value. If fewer than `window + MIN_RANK_SAMPLE`
    closes are available the distribution is too thin to rank, so we return
    50 (the neutral "medium" bucket) and the caller degrades gracefully.
    """
    if len(closes) < window + MIN_RANK_SAMPLE:
        return 50

    # One realized_vol observation per day where a full window is available,
    # capped to the lookback horizon.
    series = []
    start = max(window, len(closes) - lookback)
    for end in range(start, len(closes) + 1):
        series.append(realized_vol(closes[:end], window=window))

    latest = series[-1]
    below = sum(1 for v in series if v < latest)
    return round(100 * below / (len(series) - 1)) if len(series) > 1 else 50
