"""ATR14 with Wilder's smoothing.

Wilder's smoothing is the canonical ATR formula:
    Seed ATR = mean of first 14 True Ranges.
    Subsequent: ATR_t = (ATR_{t-1} * 13 + TR_t) / 14

True Range for bar t (t >= 1) is the max of:
    high_t - low_t
    |high_t - close_{t-1}|
    |low_t  - close_{t-1}|

For bar 0 there is no previous close; we skip it (TRs start at index 1).
We need 15 bars to compute 14 TRs, hence the minimum-length check.
"""

from typing import Sequence


def atr14(bars: Sequence[tuple[float, float, float]]) -> float:
    """Compute ATR14 (Wilder's) at the latest bar.

    `bars` is a sequence of (high, low, close) tuples ordered oldest-to-newest.
    Requires at least 15 bars (one anchor close + 14 TR observations).
    """
    if len(bars) < 15:
        raise ValueError(f"atr14 needs at least 15 bars, got {len(bars)}")

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

    # Seed: simple mean of first 14 TRs.
    atr = sum(trs[:14]) / 14
    # Wilder smoothing for subsequent TRs (TRs 15..N-1 in TR list).
    for tr in trs[14:]:
        atr = (atr * 13 + tr) / 14
    return atr
