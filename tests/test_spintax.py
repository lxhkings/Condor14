# tests/test_spintax.py
import re
from datetime import date
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from content_engine.spintax import (
    classify_iv_percentile,
    classify_vol_regime,
    render_prelude,
)
from ledger.schema import Setup

TEMPLATE_DIR = Path(__file__).parent.parent / "content_engine" / "templates"
SPINTAX_DIR = TEMPLATE_DIR / "spintax"


def _setup(*, trend_bias="bullish", iv=80) -> Setup:
    return Setup(
        id="X", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 28), target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61, atr14_at_open=4.85, sma20_at_open=190.84,
        iv_percentile_at_open=iv, trend_bias=trend_bias,
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0,  long_put_strike=195.0,
        net_credit_at_open=1.42, wing_width=5.0,
        max_profit=1.42, max_loss=3.58,
        break_even_upper=231.42, break_even_lower=198.58,
        status="open", daily_marks=[], settlement=None,
    )


def test_iv_percentile_boundaries():
    # Per spec §5.2: high if >70, low if <30, medium otherwise (inclusive of 30 and 70)
    assert classify_iv_percentile(71) == "high"
    assert classify_iv_percentile(70) == "medium"
    assert classify_iv_percentile(30) == "medium"
    assert classify_iv_percentile(29) == "low"
    assert classify_iv_percentile(0)  == "low"
    assert classify_iv_percentile(100) == "high"


def test_vol_regime_boundaries():
    # expanding if atr14 > atr60 * 1.2; contracting if < atr60 * 0.8
    assert classify_vol_regime(atr14=12.01, atr60=10.0) == "expanding"
    assert classify_vol_regime(atr14=12.0,  atr60=10.0) == "stable"   # boundary inclusive
    assert classify_vol_regime(atr14=8.0,   atr60=10.0) == "stable"
    assert classify_vol_regime(atr14=7.99,  atr60=10.0) == "contracting"


def test_render_prelude_picks_correct_template_by_trend_iv(tmp_path):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    out = render_prelude(setup=_setup(trend_bias="bullish", iv=80), atr60=4.0, jinja_env=env)
    assert "{{ vol_regime_modifier }}" not in out  # marker was rendered
    # bullish×high should mention "above its 20-day"
    assert "above" in out.lower()


def test_every_template_has_marker_exactly_once():
    failures = []
    for path in SPINTAX_DIR.glob("*.md.j2"):
        if path.name == "_modifier.md.j2":
            continue
        text = path.read_text()
        count = text.count("{{ vol_regime_modifier }}")
        if count != 1:
            failures.append((path.name, count))
    assert failures == [], f"templates with wrong marker count: {failures}"


def test_no_two_templates_share_more_than_30pct_sentences():
    """Spec §5.2: build-time check that pairs of full templates share <=30% sentences."""
    sentences_per_template = {}
    for path in SPINTAX_DIR.glob("*.md.j2"):
        if path.name == "_modifier.md.j2":
            continue
        text = re.sub(r"\{%.*?%\}", "", path.read_text(), flags=re.DOTALL)
        text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
        text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 20]
        sentences_per_template[path.name] = set(sentences)

    failures = []
    names = sorted(sentences_per_template)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = sentences_per_template[a] & sentences_per_template[b]
            base = min(len(sentences_per_template[a]), len(sentences_per_template[b]))
            if base == 0:
                continue
            ratio = len(shared) / base
            if ratio > 0.30:
                failures.append((a, b, ratio))
    assert failures == [], f"template pairs with >30% sentence overlap: {failures}"


def test_modifier_injection_preserves_sentence_boundaries():
    """After rendering with each vol_regime, no double periods / lowercase-after-period / orphaned commas."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    bad_patterns = [
        r"\.\.",            # double period
        r"\.\s+[a-z]",      # period then lowercase letter (with space between)
        r"\.\s*,",          # period then comma
        r",\s*\.",          # comma then period
    ]
    failures = []
    for trend in ("bullish", "neutral", "bearish"):
        for iv in (80, 50, 20):
            for atr_ratio in (1.5, 1.0, 0.5):  # expanding, stable, contracting
                setup = _setup(trend_bias=trend, iv=iv)
                out = render_prelude(setup=setup, atr60=setup.atr14_at_open / atr_ratio, jinja_env=env)
                for pat in bad_patterns:
                    if re.search(pat, out):
                        failures.append((trend, iv, atr_ratio, pat, out[:120]))
    assert failures == [], f"sentence-boundary violations: {failures[:3]}"


def test_render_prelude_uses_setup_variables():
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    out = render_prelude(setup=_setup(trend_bias="bullish", iv=80), atr60=4.0, jinja_env=env)
    assert "NVDA" in out
    assert "216.61" in out
    assert "190.84" in out
