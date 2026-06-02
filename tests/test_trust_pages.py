# tests/test_trust_pages.py
from datetime import date
from pathlib import Path

from content_engine.json_ld import organization_schema


def test_organization_schema_shape():
    org = organization_schema(
        base_url="https://example.com", contact_email="contact@example.com"
    )
    assert org["@type"] == "Organization"
    assert org["name"] == "QuantOptions Data Lab"
    assert org["url"] == "https://example.com/"
    assert org["contactPoint"]["email"] == "contact@example.com"


from build_site import build
from ledger.schema import Ledger, Settlement, Setup
from ledger.store import LedgerStore


def _nvda_setup() -> Setup:
    return Setup(
        id="NVDA-A", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 26), target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61, atr14_at_open=4.85, sma20_at_open=190.84,
        vol_percentile_at_open=62, trend_bias="bullish",
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0, long_put_strike=195.0,
        net_credit_at_open=1.42, wing_width=5.0,
        max_profit=1.42, max_loss=3.58,
        break_even_upper=231.42, break_even_lower=198.58,
        status="won", daily_marks=[],
        settlement=Settlement(
            settled_on=date(2026, 5, 10), final_underlying=215.0,
            breached_side=None, final_pnl_per_spread=1.42,
        ),
        atr60_at_open=4.20,
    )


def _build(tmp_path: Path) -> Path:
    """Run a full build; return the public dir. NVDA gets a full ticker page;
    all other TICKERS render placeholder pages."""
    ledger_path = tmp_path / "ledger.json"
    LedgerStore(ledger_path).save(
        Ledger(setups=[_nvda_setup()], site_launch_date=date(2026, 4, 28))
    )
    public = tmp_path / "public"
    key = tmp_path / "indexnow_key.txt"
    key.write_text("k" * 32)
    rc = build(
        ledger_path=ledger_path, public_dir=public, host="example.com",
        today=date(2026, 5, 13), indexnow_key_path=key,
        last_indexed_path=tmp_path / "last_indexed.json",
        skip_indexnow_ping=True,
    )
    assert rc == 0
    return public


def test_footer_nav_on_all_page_types(tmp_path):
    public = _build(tmp_path)
    home = (public / "index.html").read_text()
    ticker = (public / "nvda" / "index.html").read_text()      # full ticker page
    placeholder = (public / "spy" / "index.html").read_text()  # no setup -> placeholder
    for html in (home, ticker, placeholder):
        assert "/about/" in html
        assert "/privacy/" in html
        assert "/contact/" in html
        assert "/methodology/" in html


from build_site import PUBLISHER_EMAIL


def test_trust_pages_render(tmp_path):
    public = _build(tmp_path)
    for slug in ("about", "privacy", "contact"):
        page = public / slug / "index.html"
        assert page.is_file()
        assert len(page.read_text()) > 0


def test_privacy_page_has_adsense_requisites(tmp_path):
    public = _build(tmp_path)
    html = (public / "privacy" / "index.html").read_text().lower()
    assert "google" in html
    assert "cookie" in html
    assert "https://www.google.com/settings/ads" in html
    assert "aboutads.info" in html
    assert PUBLISHER_EMAIL.lower() in html


def test_contact_page_has_email(tmp_path):
    public = _build(tmp_path)
    html = (public / "contact" / "index.html").read_text()
    assert PUBLISHER_EMAIL in html
    assert f"mailto:{PUBLISHER_EMAIL}" in html


def test_sitemap_includes_trust_pages(tmp_path):
    public = _build(tmp_path)
    sitemap = (public / "sitemap.xml").read_text()
    assert "/about/" in sitemap
    assert "/privacy/" in sitemap
    assert "/contact/" in sitemap


def test_homepage_has_organization_jsonld(tmp_path):
    public = _build(tmp_path)
    html = (public / "index.html").read_text()
    assert '"@type":"Organization"' in html
    assert PUBLISHER_EMAIL in html