import pytest

from data_source.marketdata import OptionLeg
from math_engine.iron_condor import build_condor, ZeroOrNegativeCreditError

from datetime import date


def _leg(side, strike, bid, ask, *, oi=1000, vol=100, iv=0.4):
    return OptionLeg(
        underlying="NVDA",
        expiration=date(2026, 5, 16),
        side=side, strike=strike,
        bid=bid, ask=ask, mid=(bid + ask) / 2,
        open_interest=oi, volume=vol, iv=iv,
    )


def test_basic_iron_condor_math():
    # short call 230 bid 2.10, long call 235 ask 1.30 -> call credit 0.80
    # short put  200 bid 1.85, long put  195 ask 1.15 -> put credit 0.70
    # net credit = 1.50
    # wing width = 5
    # max loss = 5 - 1.50 = 3.50
    # BE upper = 230 + 1.50 = 231.50; BE lower = 200 - 1.50 = 198.50
    ic = build_condor(
        short_call=_leg("call", 230.0, bid=2.10, ask=2.20),
        long_call =_leg("call", 235.0, bid=1.20, ask=1.30),
        short_put =_leg("put",  200.0, bid=1.85, ask=1.95),
        long_put  =_leg("put",  195.0, bid=1.05, ask=1.15),
    )
    assert ic.net_credit == pytest.approx(1.50)
    assert ic.wing_width == pytest.approx(5.0)
    assert ic.max_profit == pytest.approx(1.50)
    assert ic.max_loss == pytest.approx(3.50)
    assert ic.break_even_upper == pytest.approx(231.50)
    assert ic.break_even_lower == pytest.approx(198.50)


def test_zero_or_negative_credit_raises():
    # Costs more than received -> negative credit
    with pytest.raises(ZeroOrNegativeCreditError):
        build_condor(
            short_call=_leg("call", 230.0, bid=0.50, ask=0.60),
            long_call =_leg("call", 235.0, bid=1.20, ask=1.30),
            short_put =_leg("put",  200.0, bid=0.30, ask=0.40),
            long_put  =_leg("put",  195.0, bid=1.05, ask=1.15),
        )


def test_call_and_put_wings_must_match_in_width():
    with pytest.raises(ValueError, match="wing widths"):
        build_condor(
            short_call=_leg("call", 230.0, bid=2.10, ask=2.20),
            long_call =_leg("call", 235.0, bid=1.20, ask=1.30),  # wing 5
            short_put =_leg("put",  200.0, bid=1.85, ask=1.95),
            long_put  =_leg("put",  192.5, bid=1.05, ask=1.15),  # wing 7.5
        )


def test_short_legs_must_be_correct_sides():
    with pytest.raises(ValueError, match="short_call must be a call"):
        build_condor(
            short_call=_leg("put",  230.0, bid=2.10, ask=2.20),
            long_call =_leg("call", 235.0, bid=1.20, ask=1.30),
            short_put =_leg("put",  200.0, bid=1.85, ask=1.95),
            long_put  =_leg("put",  195.0, bid=1.05, ask=1.15),
        )
