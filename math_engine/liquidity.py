"""Liquidity filter for individual option legs.

Reject any leg that fails:
    - bid > 0
    - (ask - bid) / mid <= 0.30
    - open_interest >= 100
"""

from enum import Enum

from data_source.marketdata import OptionLeg


class LiquidityRejection(Enum):
    ZERO_BID = "zero_bid"
    WIDE_SPREAD = "wide_spread"
    LOW_OI = "low_oi"


def leg_passes_liquidity(leg: OptionLeg) -> LiquidityRejection | None:
    """Return None if leg passes, else the reason it was rejected."""
    if leg.bid <= 0:
        return LiquidityRejection.ZERO_BID
    mid = (leg.bid + leg.ask) / 2
    if mid <= 0:
        return LiquidityRejection.ZERO_BID
    spread_ratio = (leg.ask - leg.bid) / mid
    if spread_ratio > 0.30:
        return LiquidityRejection.WIDE_SPREAD
    if leg.open_interest < 100:
        return LiquidityRejection.LOW_OI
    return None
