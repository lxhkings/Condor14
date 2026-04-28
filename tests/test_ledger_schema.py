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
        iv_percentile_at_open=62,
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
