"""SMA computation and SMA-relative trend bias classifier.

Trend bias buckets used by the spintax engine in Plan B:
    bullish  if close > sma * 1.005
    bearish  if close < sma * 0.995
    neutral  otherwise (within +/- 0.5% of SMA)

The 0.5% deadband prevents bias flipping on tiny intraday noise.
"""

from typing import Literal, Sequence

TrendBias = Literal["bullish", "bearish", "neutral"]


def sma(closes: Sequence[float], *, period: int = 20) -> float:
    """Simple moving average over the last `period` closes."""
    if len(closes) < period:
        raise ValueError(f"sma needs at least {period} closes, got {len(closes)}")
    window = closes[-period:]
    return sum(window) / period


def classify_trend_bias(*, close: float, sma: float) -> TrendBias:
    upper = sma * 1.005
    lower = sma * 0.995
    if close > upper:
        return "bullish"
    if close < lower:
        return "bearish"
    return "neutral"
