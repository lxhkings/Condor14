from datetime import date

from data_source.futu_client import OptionLeg
from math_engine.liquidity import LiquidityRejection, leg_passes_liquidity


def _leg(*, bid, ask, oi):
    return OptionLeg(
        underlying="NVDA", expiration=date(2026, 5, 16),
        side="call", strike=230.0,
        bid=bid, ask=ask, mid=(bid + ask) / 2 if bid + ask > 0 else 0.0,
        open_interest=oi, volume=100, iv=0.4,
    )


def test_passing_leg_returns_none():
    assert leg_passes_liquidity(_leg(bid=2.10, ask=2.20, oi=1000)) is None


def test_zero_bid_rejected():
    rej = leg_passes_liquidity(_leg(bid=0.0, ask=0.10, oi=1000))
    assert rej == LiquidityRejection.ZERO_BID


def test_wide_spread_rejected():
    # mid = 1.50, ask-bid = 1.00, ratio = 0.667 > 0.30
    rej = leg_passes_liquidity(_leg(bid=1.0, ask=2.0, oi=1000))
    assert rej == LiquidityRejection.WIDE_SPREAD


def test_spread_at_threshold_passes():
    # mid = 1.0, ask-bid = 0.30, ratio = 0.30 (boundary)
    assert leg_passes_liquidity(_leg(bid=0.85, ask=1.15, oi=1000)) is None
