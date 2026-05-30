# tests/test_ticker_track_record.py
from datetime import date
from pathlib import Path

from build_site import build
from ledger.schema import Ledger, Settlement, Setup
from ledger.store import LedgerStore


def _nvda_setup(*, id, start, settled_on=None, status="open", pnl=0.0):
    return Setup(
        id=id, ticker="NVDA", sector="Semiconductors",
        start_date=start, target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61, atr14_at_open=4.85, sma20_at_open=190.84,
        iv_percentile_at_open=62, trend_bias="bullish",
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0, long_put_strike=195.0,
        net_credit_at_open=1.42, wing_width=5.0,
        max_profit=1.42, max_loss=3.58,
        break_even_upper=231.42, break_even_lower=198.58,
        status=status, daily_marks=[],
        settlement=(
            Settlement(
                settled_on=settled_on, final_underlying=215.0,
                breached_side=None, final_pnl_per_spread=pnl,
            ) if settled_on else None
        ),
    )


def _seed_settled(path: Path) -> None:
    setups = [
        _nvda_setup(id="NVDA-A", start=date(2026, 4, 26),
                    settled_on=date(2026, 5, 10), status="won", pnl=1.42),
        _nvda_setup(id="NVDA-B", start=date(2026, 4, 28),
                    settled_on=date(2026, 5, 12), status="lost", pnl=-3.58),
    ]
    LedgerStore(path).save(
        Ledger(setups=setups, site_launch_date=date(2026, 4, 28))
    )


def _build(tmp_path, ledger_path) -> str:
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
    return (public / "nvda" / "index.html").read_text()


def test_track_record_renders_with_settled_setups(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _seed_settled(ledger_path)
    html = _build(tmp_path, ledger_path)
    assert "Track Record" in html
    assert "Across 2 settled" in html
    assert "50% of the time" in html
    # cumulative 1.42 - 3.58 = -2.16
    assert "$-2.16" in html
    # worst single loss
    assert "$-3.58" in html


def test_track_record_hidden_when_no_settled(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    # Single OPEN setup, never settled -> sample_size 0 for NVDA
    setup = _nvda_setup(id="NVDA-OPEN", start=date(2026, 5, 1))
    LedgerStore(ledger_path).save(
        Ledger(setups=[setup], site_launch_date=date(2026, 4, 28))
    )
    html = _build(tmp_path, ledger_path)
    assert "Track Record" not in html
