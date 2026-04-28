"""ATR-anchored Iron Condor strike picker.

Anchors:
    short_call_anchor = spot + 1.5 * atr14
    short_put_anchor  = spot - 1.5 * atr14

Snap each anchor to the nearest LISTED strike. Wing width target is
0.5 * atr14, floored at one strike spacing increment, snapped to the
nearest above (calls) or below (puts) the wing target.

Raises NoValidIronCondorError if any of these invariants fail:
    - available_strikes empty
    - short call anchor and short put anchor snap to the same strike
    - long-call wing strike is not present in the chain (above short_call)
    - long-put  wing strike is not present in the chain (below short_put)
    - final ordering (lp < sp < sc < lc) does not hold
"""

from typing import Sequence


class NoValidIronCondorError(Exception):
    """No valid 4-leg condor can be constructed from the given chain."""


def _nearest(values: list[float], target: float) -> float:
    return min(values, key=lambda v: abs(v - target))


def _min_spacing(values: list[float]) -> float:
    pairs = zip(values, values[1:])
    return min(b - a for a, b in pairs)


def pick_strikes(
    *,
    spot: float,
    atr14: float,
    available_strikes: Sequence[float],
) -> tuple[float, float, float, float]:
    """Return (short_call, long_call, short_put, long_put)."""
    strikes = sorted(set(float(s) for s in available_strikes))
    if not strikes:
        raise NoValidIronCondorError("available_strikes is empty")
    if len(strikes) < 2:
        raise NoValidIronCondorError("need at least 2 strikes to compute spacing")

    short_call_anchor = spot + 1.5 * atr14
    short_put_anchor = spot - 1.5 * atr14

    short_call = _nearest(strikes, short_call_anchor)
    short_put = _nearest(strikes, short_put_anchor)

    if short_call == short_put:
        raise NoValidIronCondorError(
            f"short call and short put collapse to same strike {short_call}"
        )

    spacing = _min_spacing(strikes)
    wing_target = max(0.5 * atr14, spacing)

    long_call_target = short_call + wing_target
    long_put_target = short_put - wing_target

    # Long call: smallest listed strike >= long_call_target
    long_call_candidates = [s for s in strikes if s >= long_call_target and s > short_call]
    if not long_call_candidates:
        raise NoValidIronCondorError(
            f"no listed strike for long call wing above {long_call_target}"
        )
    long_call = min(long_call_candidates)

    # Long put: largest listed strike <= long_put_target
    long_put_candidates = [s for s in strikes if s <= long_put_target and s < short_put]
    if not long_put_candidates:
        raise NoValidIronCondorError(
            f"no listed strike for long put wing below {long_put_target}"
        )
    long_put = max(long_put_candidates)

    if not (long_put < short_put < short_call < long_call):
        raise NoValidIronCondorError(
            f"strike ordering invalid: {long_put} {short_put} {short_call} {long_call}"
        )

    return short_call, long_call, short_put, long_put
