"""Iron Condor calculator using conservative bid-ask quoting.

Convention (per design spec §4.6):
    Short legs priced at BID  (worst realistic fill received)
    Long  legs priced at ASK  (worst realistic fill paid)

    net_credit  = (short_call.bid + short_put.bid) - (long_call.ask + long_put.ask)
    wing_width  = long_call.strike - short_call.strike
                = short_put.strike - long_put.strike   (must match)
    max_profit  = net_credit
    max_loss    = wing_width - net_credit
    BE_upper    = short_call.strike + net_credit
    BE_lower    = short_put.strike  - net_credit
"""

from dataclasses import dataclass

from data_source.marketdata import OptionLeg


class ZeroOrNegativeCreditError(Exception):
    """Net credit <= 0 --- no setup edge, skip."""


@dataclass(frozen=True)
class IronCondor:
    short_call: OptionLeg
    long_call: OptionLeg
    short_put: OptionLeg
    long_put: OptionLeg
    net_credit: float
    wing_width: float
    max_profit: float
    max_loss: float
    break_even_upper: float
    break_even_lower: float


def build_condor(
    *,
    short_call: OptionLeg,
    long_call: OptionLeg,
    short_put: OptionLeg,
    long_put: OptionLeg,
) -> IronCondor:
    if short_call.side != "call":
        raise ValueError("short_call must be a call")
    if long_call.side != "call":
        raise ValueError("long_call must be a call")
    if short_put.side != "put":
        raise ValueError("short_put must be a put")
    if long_put.side != "put":
        raise ValueError("long_put must be a put")

    if not (long_put.strike < short_put.strike < short_call.strike < long_call.strike):
        raise ValueError("strike ordering invalid")

    call_wing = long_call.strike - short_call.strike
    put_wing = short_put.strike - long_put.strike
    if abs(call_wing - put_wing) > 1e-9:
        raise ValueError(
            f"call and put wing widths must match ({call_wing} vs {put_wing})"
        )
    wing_width = call_wing

    net_credit = (
        short_call.bid + short_put.bid - long_call.ask - long_put.ask
    )
    if net_credit <= 0:
        raise ZeroOrNegativeCreditError(f"net_credit={net_credit:.4f}")

    return IronCondor(
        short_call=short_call,
        long_call=long_call,
        short_put=short_put,
        long_put=long_put,
        net_credit=round(net_credit, 4),
        wing_width=round(wing_width, 4),
        max_profit=round(net_credit, 4),
        max_loss=round(wing_width - net_credit, 4),
        break_even_upper=round(short_call.strike + net_credit, 4),
        break_even_lower=round(short_put.strike - net_credit, 4),
    )
