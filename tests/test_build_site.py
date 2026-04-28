# tests/test_build_site.py
import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from build_site import build
from ledger.schema import Ledger, Settlement, Setup
from ledger.store import LedgerStore


def _seed_empty_ledger(path: Path) -> None:
    LedgerStore(path).save(Ledger(site_launch_date=date(2026, 4, 28)))


def _seed_ledger_with_one_open(path: Path) -> None:
    setup = Setup(
        id="NVDA-2026-04-28", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 28), target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61, atr14_at_open=4.85, sma20_at_open=190.84,
        iv_percentile_at_open=62, trend_bias="bullish",
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0,  long_put_strike=195.0,
        net_credit_at_open=1.42, wing_width=5.0,
        max_profit=1.42, max_loss=3.58,
        break_even_upper=231.42, break_even_lower=198.58,
        status="open", daily_marks=[], settlement=None,
    )
    ledger = Ledger(setups=[setup], site_launch_date=date(2026, 4, 28))
    LedgerStore(path).save(ledger)


def test_build_with_empty_ledger_produces_all_pages(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _seed_empty_ledger(ledger_path)
    public = tmp_path / "public"
    indexnow_key = tmp_path / "indexnow_key.txt"
    indexnow_key.write_text("abc123def456abc123def456abc123de")

    rc = build(
        ledger_path=ledger_path,
        public_dir=public,
        host="example.com",
        today=date(2026, 4, 28),
        indexnow_key_path=indexnow_key,
        last_indexed_path=tmp_path / "last_indexed.json",
        skip_indexnow_ping=True,
    )
    assert rc == 0
    assert (public / "index.html").exists()
    assert (public / "methodology" / "index.html").exists()
    # All 20 ticker pages exist (lowercase paths)
    from config import TICKERS

    for t in TICKERS:
        assert (public / t.lower() / "index.html").exists(), f"missing page for {t}"
    assert (public / "sitemap.xml").exists()
    assert (public / "robots.txt").exists()
    assert (public / "abc123def456abc123def456abc123de.txt").exists()


def test_build_renders_setup_data_into_ticker_page(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _seed_ledger_with_one_open(ledger_path)
    public = tmp_path / "public"
    indexnow_key = tmp_path / "indexnow_key.txt"
    indexnow_key.write_text("k" * 32)

    build(
        ledger_path=ledger_path, public_dir=public,
        host="example.com", today=date(2026, 4, 28),
        indexnow_key_path=indexnow_key,
        last_indexed_path=tmp_path / "last_indexed.json",
        skip_indexnow_ping=True,
    )
    nvda_html = (public / "nvda" / "index.html").read_text()
    assert "216.61" in nvda_html
    assert "NVDA 14-Day Iron Condor" in nvda_html
    assert '<script type="application/ld+json">' in nvda_html
    # Disclaimer is hardcoded (per spec §7.2)
    assert "Educational purposes only" in nvda_html


def test_build_returns_nonzero_on_compliance_violation(tmp_path, monkeypatch):
    # Patch the compliance checker to report a violation
    import build_site

    monkeypatch.setattr(
        build_site,
        "check_hypothetical_allowlist",
        lambda public_dir: [(
            Path("public/nvda/index.html"),
            5,
            "...hypothetical...",
        )],
    )
    ledger_path = tmp_path / "ledger.json"
    _seed_empty_ledger(ledger_path)
    public = tmp_path / "public"
    indexnow_key = tmp_path / "indexnow_key.txt"
    indexnow_key.write_text("k" * 32)

    rc = build(
        ledger_path=ledger_path, public_dir=public,
        host="example.com", today=date(2026, 4, 28),
        indexnow_key_path=indexnow_key,
        last_indexed_path=tmp_path / "last_indexed.json",
        skip_indexnow_ping=True,
    )
    assert rc != 0


def test_build_respects_cutover_for_homepage_choice(tmp_path):
    # 200 settled setups + 30 days since first -> Mode B
    from datetime import timedelta

    settled = []
    first_date = date(2026, 1, 1)
    for i in range(250):
        d = first_date + timedelta(days=i // 5)  # 5 settlements per "day"
        settled.append(Setup(
            id=f"X-{i}", ticker="NVDA", sector="Semiconductors",
            start_date=d - timedelta(days=14), target_exit_date=d, expiry_used=d,
            underlying_at_open=100.0, atr14_at_open=2.0, sma20_at_open=100.0,
            iv_percentile_at_open=50, trend_bias="neutral",
            short_call_strike=105.0, long_call_strike=110.0,
            short_put_strike=95.0,  long_put_strike=90.0,
            net_credit_at_open=1.0, wing_width=5.0,
            max_profit=1.0, max_loss=4.0,
            break_even_upper=106.0, break_even_lower=94.0,
            status="won", daily_marks=[],
            settlement=Settlement(
                settled_on=d, final_underlying=100.0,
                breached_side=None, final_pnl_per_spread=100.0,
            ),
        ))
    ledger_path = tmp_path / "ledger.json"
    LedgerStore(ledger_path).save(
        Ledger(setups=settled, site_launch_date=first_date,
               first_settlement_date=first_date)
    )
    public = tmp_path / "public"
    indexnow_key = tmp_path / "indexnow_key.txt"
    indexnow_key.write_text("k" * 32)

    build(
        ledger_path=ledger_path, public_dir=public,
        host="example.com",
        today=first_date + timedelta(days=60),  # well past cutover
        indexnow_key_path=indexnow_key,
        last_indexed_path=tmp_path / "last_indexed.json",
        skip_indexnow_ping=True,
    )
    home = (public / "index.html").read_text()
    assert "Live 30-Day Hold-to-Expiration Performance" in home
    assert "Daily Iron Condor Volatility Screener" not in home
