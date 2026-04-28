"""14-day hold-to-expiration P&L evaluator.

Per design spec §4.7:
    won  if short_put <= close <= short_call
    lost otherwise

For a lost setup:
    breach_distance = max(short_put - close, close - short_call, 0)
    capped_loss     = min(breach_distance, wing_width)
    final_pnl_per_spread = (net_credit - capped_loss) * 100   (negative)

For a won setup:
    final_pnl_per_spread = net_credit * 100   (positive)

Per-spread math: each spread represents 100 shares of underlying exposure.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Settlement:
    status: Literal["won", "lost"]
    breached_side: Literal["upper", "lower"] | None
    final_pnl_per_spread: float


def evaluate_settlement(
    *,
    underlying_close: float,
    short_call: float,
    short_put: float,
    wing_width: float,
    net_credit: float,
) -> Settlement:
    if short_put <= underlying_close <= short_call:
        return Settlement(
            status="won",
            breached_side=None,
            final_pnl_per_spread=round(net_credit * 100, 2),
        )
    if underlying_close > short_call:
        breach_distance = underlying_close - short_call
        side: Literal["upper", "lower"] = "upper"
    else:
        breach_distance = short_put - underlying_close
        side = "lower"

    capped_loss = min(breach_distance, wing_width)
    pnl = (net_credit - capped_loss) * 100
    return Settlement(
        status="lost",
        breached_side=side,
        final_pnl_per_spread=round(pnl, 2),
    )
