"""Spintax engine: select prelude template by (trend_bias, iv_percentile),
inject vol_regime modifier sentence, render with setup variables.

Per spec §5.2:
    iv_percentile bucketing: high if >70, low if <30, medium otherwise
    vol_regime bucketing: expanding if atr14 > atr60*1.2, contracting if < atr60*0.8
"""

from typing import Literal

from jinja2 import Environment

from ledger.schema import Setup

IvBucket = Literal["high", "medium", "low"]
VolRegime = Literal["expanding", "contracting", "stable"]


def classify_vol_percentile(p: int) -> IvBucket:
    if p > 70:
        return "high"
    if p < 30:
        return "low"
    return "medium"


def classify_vol_regime(*, atr14: float, atr60: float) -> VolRegime:
    if atr60 <= 0:
        return "stable"
    ratio = atr14 / atr60
    if ratio > 1.2:
        return "expanding"
    if ratio < 0.8:
        return "contracting"
    return "stable"


def _modifier_for(regime: VolRegime) -> str:
    if regime == "expanding":
        return (
            "Volatility has expanded sharply over the past two weeks, with the "
            "14-day ATR running well above its 60-day average — premiums are "
            "richer than usual but tail risk is also elevated."
        )
    if regime == "contracting":
        return (
            "Volatility is contracting from recent highs, compressing the "
            "premium envelope and tightening the breakeven band."
        )
    return ""


def render_prelude(
    *, setup: Setup, atr60: float, jinja_env: Environment,
    track_record: dict | None = None,
) -> str:
    vol_bucket = classify_vol_percentile(setup.vol_percentile_at_open)
    regime = classify_vol_regime(atr14=setup.atr14_at_open, atr60=atr60)
    template_name = f"spintax/{setup.trend_bias}_{vol_bucket}.md.j2"
    template = jinja_env.get_template(template_name)
    return template.render(
        ticker=setup.ticker,
        underlying_at_open=setup.underlying_at_open,
        atr14_at_open=setup.atr14_at_open,
        sma20_at_open=setup.sma20_at_open,
        vol_percentile_at_open=setup.vol_percentile_at_open,
        vol_regime_modifier=_modifier_for(regime),
        track_record=track_record,
    )
