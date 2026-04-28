import pytest

from math_engine.sma import classify_trend_bias, sma


def test_sma_raises_when_too_few_bars():
    with pytest.raises(ValueError, match="at least 20"):
        sma([1.0] * 19, period=20)


def test_sma_of_constant_series():
    assert sma([5.0] * 20, period=20) == pytest.approx(5.0)


def test_sma_uses_last_n_values_only():
    # 30 closes, only the last 20 should matter for SMA20.
    closes = [1.0] * 10 + [10.0] * 20
    assert sma(closes, period=20) == pytest.approx(10.0)


def test_classify_bullish_when_close_above_sma_by_more_than_half_percent():
    assert classify_trend_bias(close=100.6, sma=100.0) == "bullish"


def test_classify_bearish_when_close_below_sma_by_more_than_half_percent():
    assert classify_trend_bias(close=99.4, sma=100.0) == "bearish"


def test_classify_neutral_within_half_percent_band():
    assert classify_trend_bias(close=100.4, sma=100.0) == "neutral"
    assert classify_trend_bias(close=99.6, sma=100.0) == "neutral"
    assert classify_trend_bias(close=100.0, sma=100.0) == "neutral"
