from datetime import date

from ledger.schema import (
    DailyMark,
    Ledger,
    Settlement,
    Setup,
    SkippedEntry,
    ledger_from_json,
    ledger_to_json,
)


def _setup() -> Setup:
    return Setup(
        id="NVDA-2026-04-28",
        ticker="NVDA",
        sector="Semiconductors",
        start_date=date(2026, 4, 28),
        target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61,
        atr14_at_open=4.85,
        sma20_at_open=190.84,
        vol_percentile_at_open=62,
        trend_bias="bullish",
        short_call_strike=230.0,
        long_call_strike=235.0,
        short_put_strike=200.0,
        long_put_strike=195.0,
        net_credit_at_open=1.42,
        wing_width=5.0,
        max_profit=1.42,
        max_loss=3.58,
        break_even_upper=231.42,
        break_even_lower=198.58,
        status="open",
        daily_marks=[],
        settlement=None,
    )


def test_setup_round_trip_json():
    setup = _setup()
    blob = ledger_to_json(Ledger(setups=[setup], skipped=[]))
    out = ledger_from_json(blob)
    assert out.setups == [setup]
    assert out.skipped == []


def test_setup_with_settlement_round_trip():
    setup = _setup()
    settled = Setup(
        **{**setup.__dict__,
           "status": "won",
           "settlement": Settlement(
               settled_on=date(2026, 5, 12),
               final_underlying=215.0,
               breached_side=None,
               final_pnl_per_spread=142.0,
           ),
           "daily_marks": [
               DailyMark(date=date(2026, 4, 29), underlying_close=218.0,
                         breached_short=False),
           ],
        }
    )
    ledger = Ledger(setups=[settled], skipped=[])
    out = ledger_from_json(ledger_to_json(ledger))
    assert out.setups[0].settlement is not None
    assert out.setups[0].settlement.final_pnl_per_spread == 142.0
    assert out.setups[0].daily_marks[0].underlying_close == 218.0


def test_skipped_entries_round_trip():
    ledger = Ledger(
        setups=[],
        skipped=[SkippedEntry(ticker="PLTR", date=date(2026, 4, 28),
                              reason="no_liquid_strikes")],
    )
    out = ledger_from_json(ledger_to_json(ledger))
    assert out.skipped[0].ticker == "PLTR"
    assert out.skipped[0].reason == "no_liquid_strikes"


def test_empty_ledger_round_trip():
    ledger = Ledger(setups=[], skipped=[])
    out = ledger_from_json(ledger_to_json(ledger))
    assert out == ledger


def test_from_json_reads_legacy_iv_key_and_missing_atr60():
    import json

    from ledger.schema import SCHEMA_VERSION, ledger_from_json

    s = _setup()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "site_launch_date": None, "first_settlement_date": None, "last_run": None,
        "skipped": [],
        "setups": [{
            "id": s.id, "ticker": s.ticker, "sector": s.sector,
            "start_date": s.start_date.isoformat(),
            "target_exit_date": s.target_exit_date.isoformat(),
            "expiry_used": s.expiry_used.isoformat(),
            "underlying_at_open": s.underlying_at_open,
            "atr14_at_open": s.atr14_at_open, "sma20_at_open": s.sma20_at_open,
            "iv_percentile_at_open": 73,  # legacy key — no vol_/atr60_ keys
            "trend_bias": s.trend_bias,
            "short_call_strike": s.short_call_strike, "long_call_strike": s.long_call_strike,
            "short_put_strike": s.short_put_strike, "long_put_strike": s.long_put_strike,
            "net_credit_at_open": s.net_credit_at_open, "wing_width": s.wing_width,
            "max_profit": s.max_profit, "max_loss": s.max_loss,
            "break_even_upper": s.break_even_upper, "break_even_lower": s.break_even_lower,
            "status": s.status, "daily_marks": [], "settlement": None,
        }],
    }
    out = ledger_from_json(json.dumps(payload))
    loaded = out.setups[0]
    assert loaded.vol_percentile_at_open == 73   # read from legacy iv key
    assert loaded.atr60_at_open == 0.0           # missing → default


def test_schema_version_and_metadata_preserved():
    from datetime import datetime, timezone
    ledger = Ledger(
        setups=[],
        skipped=[],
        site_launch_date=date(2026, 4, 28),
        first_settlement_date=date(2026, 5, 12),
        last_run=datetime(2026, 5, 13, 22, 0, tzinfo=timezone.utc),
    )
    blob = ledger_to_json(ledger)
    assert '"schema_version": 1' in blob
    out = ledger_from_json(blob)
    assert out.site_launch_date == date(2026, 4, 28)
    assert out.first_settlement_date == date(2026, 5, 12)
    assert out.last_run is not None
