import pytest

from math_engine.atr import atr14, atr60


def _bars(*tuples):
    """Helper: bars given as (high, low, close)."""
    return list(tuples)


def test_atr14_raises_when_too_few_bars():
    bars = _bars(*[(10.0, 9.0, 9.5)] * 14)  # only 14 bars
    with pytest.raises(ValueError, match="at least 15"):
        atr14(bars)


def test_atr14_constant_bars_yields_constant_range():
    # 16 identical bars: every TR == 1.0, ATR14 == 1.0 throughout
    bars = _bars(*[(11.0, 10.0, 10.5)] * 16)
    assert atr14(bars) == pytest.approx(1.0)


def test_atr14_wilder_smoothing_on_known_sequence():
    # Hand-computed reference:
    # Bars 1..15 produce 14 TRs. We construct a sequence where TR is constant
    # at 2.0 for the first 14, then jumps to 4.0 on bar 16 (the 15th TR).
    # Seed ATR = mean(2.0 x 14) = 2.0
    # After Wilder step: ATR = (2.0 * 13 + 4.0) / 14 = 30.0 / 14 ≈ 2.142857
    bars = []
    # Bar 0: anchor close
    bars.append((10.0, 8.0, 9.0))
    # Bars 1..14: each has H-L=2.0 and same close as bar 0 -> TR=2.0
    for _ in range(14):
        bars.append((10.0, 8.0, 9.0))
    # Bar 15: H=12, L=8, close=11. TR = max(4, |12-9|, |8-9|) = 4.0
    bars.append((12.0, 8.0, 11.0))
    assert len(bars) == 16
    assert atr14(bars) == pytest.approx(30.0 / 14, rel=1e-9)


def test_atr14_uses_prev_close_for_gap():
    # 16 bars with a gap-up on the last bar.
    # Bars 1..14 all yield TR = 1.0 (H=11, L=10, prev_close=10.5).
    # Bar 15: H=15, L=14, prev_close=10.5. TR = max(1, |15-10.5|, |14-10.5|) = 4.5
    # Seed ATR after first 14 TRs: 1.0
    # After Wilder step: (1.0 * 13 + 4.5) / 14 = 17.5 / 14 = 1.25
    bars = [(11.0, 10.0, 10.5)] * 15 + [(15.0, 14.0, 14.5)]
    assert atr14(bars) == pytest.approx(17.5 / 14, rel=1e-9)


def test_atr60_needs_at_least_61_bars():
    bars = [(10.0, 9.0, 9.5)] * 60
    with pytest.raises(ValueError):
        atr60(bars)


def test_atr60_constant_range_equals_range():
    # 61 bars, each with a 1.0 high-low range and flat closes -> ATR == 1.0
    bars = [(10.0, 9.0, 9.5)] * 61
    assert atr60(bars) == pytest.approx(1.0)
