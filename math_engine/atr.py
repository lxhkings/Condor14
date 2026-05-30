"""ATR with Wilder's smoothing.

Wilder's smoothing is the canonical ATR formula:
    Seed ATR = mean of first `period` True Ranges.
    Subsequent: ATR_t = (ATR_{t-1} * (period-1) + TR_t) / period

True Range for bar t (t >= 1) is the max of:
    high_t - low_t
    |high_t - close_{t-1}|
    |low_t  - close_{t-1}|

For bar 0 there is no previous close; we skip it (TRs start at index 1).
We need period+1 bars to compute period TRs, hence the minimum-length check.
"""

from typing import Sequence


def _atr(bars: Sequence[tuple[float, float, float]], period: int) -> float:
    """Wilder's ATR over `period` true ranges at the latest bar.

    `bars` = (high, low, close) tuples, oldest-to-newest. Needs `period + 1`
    bars (one anchor close + `period` TR observations).
    """
    if len(bars) < period + 1:
        raise ValueError(f"atr{period} needs at least {period + 1} bars, got {len(bars)}")

    trs: list[float] = []
    for i in range(1, len(bars)):
        high_t, low_t, _close_t = bars[i]
        prev_close = bars[i - 1][2]
        tr = max(
            high_t - low_t,
            abs(high_t - prev_close),
            abs(low_t - prev_close),
        )
        trs.append(tr)

    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def atr14(bars: Sequence[tuple[float, float, float]]) -> float:
    """Compute ATR14 (Wilder's) at the latest bar. Requires at least 15 bars."""
    return _atr(bars, 14)


def atr60(bars: Sequence[tuple[float, float, float]]) -> float:
    """Compute ATR60 (Wilder's) at the latest bar. Requires at least 61 bars."""
    return _atr(bars, 60)
