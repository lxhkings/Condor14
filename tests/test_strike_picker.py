import pytest

from math_engine.strike_picker import NoValidIronCondorError, pick_strikes


def test_normal_case_returns_4_distinct_ordered_strikes():
    # Spot 216.61, ATR 4.85.
    # Anchors: short_call ~ 223.89, short_put ~ 209.34
    # Wing target: 0.5 * 4.85 = 2.43
    # Available strikes at $5 spacing: 195, 200, 205, 210, 215, 220, 225, 230, 235
    available = [195.0, 200.0, 205.0, 210.0, 215.0, 220.0, 225.0, 230.0, 235.0]
    sc, lc, sp, lp = pick_strikes(spot=216.61, atr14=4.85, available_strikes=available)
    assert lp < sp < sc < lc
    # Anchors snap to nearest listed: 225 (closest to 223.89), 210 (closest to 209.34)
    assert sc == 225.0
    assert sp == 210.0
    # Wing width = max(2.43, min spacing). Min spacing here is 5.0, so wing = 5.0
    assert lc == 230.0
    assert lp == 205.0


def test_strikes_with_05_spacing_use_wing_at_least_one_increment():
    # Low-priced ticker with $0.50 spacing; ATR small.
    available = [i * 0.5 for i in range(40, 60)]  # 20.0, 20.5, ... 29.5
    sc, lc, sp, lp = pick_strikes(spot=24.5, atr14=1.0, available_strikes=available)
    # Anchors: short_call = 26.0, short_put = 23.0
    # Wing target: 0.5; min spacing 0.5 — wing = 0.5
    assert sc == 26.0
    assert sp == 23.0
    assert lc == 26.5
    assert lp == 22.5


def test_raises_when_anchors_collapse_to_same_strike():
    # ATR so small that both anchors round to the same listed strike.
    # spot=100, ATR=0.1: short_call_anchor=100.15, short_put_anchor=99.85
    # listed strikes at $5 spacing -> both snap to 100 -> collapse
    available = [85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0]
    with pytest.raises(NoValidIronCondorError, match="collapse"):
        pick_strikes(spot=100.0, atr14=0.1, available_strikes=available)


def test_raises_when_wings_cannot_be_placed():
    # Spot 100, ATR 4. Anchors short_call=106, short_put=94.
    # available_strikes only contains 95, 105 (no wings outside).
    available = [95.0, 105.0]
    with pytest.raises(NoValidIronCondorError, match="wing"):
        pick_strikes(spot=100.0, atr14=4.0, available_strikes=available)


def test_raises_when_available_strikes_empty():
    with pytest.raises(NoValidIronCondorError, match="empty"):
        pick_strikes(spot=100.0, atr14=4.0, available_strikes=[])
