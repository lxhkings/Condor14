import math

import pytest

from math_engine.volatility import realized_vol, vol_percentile


def test_realized_vol_flat_series_is_zero():
    closes = [100.0] * 25
    assert realized_vol(closes, window=20) == pytest.approx(0.0)


def test_realized_vol_known_alternating_series():
    # Alternating +1%/-1% log-ish moves give a positive, finite annualized vol.
    closes = [100.0]
    for i in range(1, 25):
        closes.append(closes[-1] * (1.01 if i % 2 else 1 / 1.01))
    v = realized_vol(closes, window=20)
    assert v > 0.0
    assert math.isfinite(v)


def test_realized_vol_too_few_closes_raises():
    with pytest.raises(ValueError):
        realized_vol([100.0, 101.0], window=20)


def test_vol_percentile_high_when_latest_window_most_volatile():
    # Calm for a long lookback, then a violent last 20 days -> high percentile.
    calm = [100.0 + 0.01 * i for i in range(260)]
    violent = []
    price = calm[-1]
    for i in range(20):
        price *= 1.08 if i % 2 else 1 / 1.08
        violent.append(price)
    closes = calm + violent
    assert vol_percentile(closes, window=20, lookback=252) >= 90


def test_vol_percentile_low_when_latest_window_calmest():
    violent = [100.0]
    for i in range(260):
        violent.append(violent[-1] * (1.05 if i % 2 else 1 / 1.05))
    calm = [violent[-1] + 0.001 * i for i in range(20)]
    closes = violent + calm
    assert vol_percentile(closes, window=20, lookback=252) <= 10


def test_vol_percentile_insufficient_history_returns_50():
    assert vol_percentile([100.0] * 25, window=20, lookback=252) == 50
