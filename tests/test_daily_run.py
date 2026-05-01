from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from data_source.cache import BarRow
from data_source.futu_client import OptionLeg, Quote
from ledger.schema import Settlement, Setup
from ledger.store import LedgerStore


def _bars(ticker: str, end: date, n: int = 25) -> list[BarRow]:
    """Generate n daily bars ending on `end`. ATR/SMA are well-defined."""
    from datetime import timedelta
    rows = []
    price = 200.0
    for i in range(n):
        d = end - timedelta(days=(n - 1 - i))
        rows.append(BarRow(
            ticker=ticker, bar_date=d,
            open=price, high=price + 2.0, low=price - 2.0,
            close=price + 0.5, volume=1_000_000,
        ))
        price += 0.5
    return rows


def _legs(expiration: date) -> list[OptionLeg]:
    """One usable iron condor across 4 strikes (195, 200, 230, 235) for spot ~216."""
    base = dict(underlying="NVDA", expiration=expiration,
                volume=500, iv=0.4)
    return [
        OptionLeg(side="put",  strike=195.0, bid=1.05, ask=1.15, mid=1.10,
                  open_interest=1500, **base),
        OptionLeg(side="put",  strike=200.0, bid=1.85, ask=1.95, mid=1.90,
                  open_interest=2000, **base),
        OptionLeg(side="call", strike=230.0, bid=2.10, ask=2.20, mid=2.15,
                  open_interest=2500, **base),
        OptionLeg(side="call", strike=235.0, bid=1.20, ask=1.30, mid=1.25,
                  open_interest=1800, **base),
    ]


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    client.daily_bars.return_value = _bars("NVDA", end=date(2026, 4, 28), n=25)
    client.quote.return_value = Quote(
        ticker="NVDA", last=216.61, bid=216.55, ask=216.65,
        updated=datetime(2026, 4, 28, 20, 0, tzinfo=timezone.utc),
    )
    # Use May 12 (14 days out) so pick_expiration's 13-16 day window passes
    client.option_chain.return_value = _legs(expiration=date(2026, 5, 12))
    return client


def test_run_opens_a_setup_for_a_normal_ticker(tmp_path, fake_client, monkeypatch):
    from daily_run import run

    # Patch the trading-day guard so we always run
    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations",
                        lambda client, ticker: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", ["NVDA"])
    monkeypatch.setattr("daily_run.SECTORS", {"NVDA": "Semiconductors"})

    store = LedgerStore(tmp_path / "ledger.json")
    cache_path = tmp_path / "cache.sqlite"

    run(today=date(2026, 4, 28), client=fake_client, store=store, cache_path=cache_path)

    out = store.load()
    assert len(out.setups) == 1
    s = out.setups[0]
    assert s.ticker == "NVDA"
    assert s.status == "open"
    assert s.short_call_strike == 230.0 or s.short_call_strike == 220.0  # depends on ATR
    assert s.net_credit_at_open > 0
    assert out.site_launch_date == date(2026, 4, 28)


def test_run_settles_open_setup_at_expiry(tmp_path, fake_client, monkeypatch):
    from daily_run import run

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations",
                        lambda client, ticker: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", [])  # don't open new setups
    monkeypatch.setattr("daily_run.SECTORS", {})

    # Seed an open setup whose target_exit_date is today
    seed_open = Setup(
        id="NVDA-2026-04-14", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 14), target_exit_date=date(2026, 4, 28),
        expiry_used=date(2026, 4, 30),
        underlying_at_open=210.0, atr14_at_open=4.0, sma20_at_open=200.0,
        iv_percentile_at_open=50, trend_bias="bullish",
        short_call_strike=220.0, long_call_strike=225.0,
        short_put_strike=200.0, long_put_strike=195.0,
        net_credit_at_open=1.50, wing_width=5.0,
        max_profit=1.50, max_loss=3.50,
        break_even_upper=221.50, break_even_lower=198.50,
        status="open", daily_marks=[], settlement=None,
    )
    from ledger.schema import Ledger
    store = LedgerStore(tmp_path / "ledger.json")
    store.save(Ledger(setups=[seed_open], site_launch_date=date(2026, 4, 14)))

    # Today's underlying is 216.61 -> inside [200, 220] => won
    run(today=date(2026, 4, 28), client=fake_client, store=store,
        cache_path=tmp_path / "cache.sqlite")

    out = store.load()
    settled = out.setups[0]
    assert settled.status == "won"
    assert settled.settlement is not None
    assert settled.settlement.final_pnl_per_spread == pytest.approx(150.0)
    assert out.first_settlement_date == date(2026, 4, 28)


def test_run_skips_ticker_when_no_credit(tmp_path, fake_client, monkeypatch):
    """If build_condor raises ZeroOrNegativeCreditError, ticker logged in skipped[]."""
    from daily_run import run

    # All bids zero -> liquidity rejection. Use bids that pass liquidity
    # but produce negative net credit: long asks > short bids.
    bad_legs = [
        OptionLeg(underlying="NVDA", expiration=date(2026, 5, 12), side="put",
                  strike=195.0, bid=1.50, ask=1.55, mid=1.525,
                  open_interest=1500, volume=500, iv=0.4),
        OptionLeg(underlying="NVDA", expiration=date(2026, 5, 12), side="put",
                  strike=200.0, bid=1.55, ask=1.60, mid=1.575,
                  open_interest=2000, volume=500, iv=0.4),
        OptionLeg(underlying="NVDA", expiration=date(2026, 5, 12), side="call",
                  strike=230.0, bid=1.55, ask=1.60, mid=1.575,
                  open_interest=2500, volume=500, iv=0.4),
        OptionLeg(underlying="NVDA", expiration=date(2026, 5, 12), side="call",
                  strike=235.0, bid=1.50, ask=1.55, mid=1.525,
                  open_interest=1800, volume=500, iv=0.4),
    ]
    fake_client.option_chain.return_value = bad_legs

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations",
                        lambda client, ticker: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", ["NVDA"])
    monkeypatch.setattr("daily_run.SECTORS", {"NVDA": "Semiconductors"})

    store = LedgerStore(tmp_path / "ledger.json")
    run(today=date(2026, 4, 28), client=fake_client, store=store,
        cache_path=tmp_path / "cache.sqlite")

    out = store.load()
    assert out.setups == []
    assert any(e.ticker == "NVDA" for e in out.skipped)


def test_run_exits_early_on_non_trading_day(tmp_path, fake_client, monkeypatch):
    from daily_run import run

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: False)
    store = LedgerStore(tmp_path / "ledger.json")
    run(today=date(2026, 5, 3), client=fake_client, store=store,
        cache_path=tmp_path / "cache.sqlite")
    assert not (tmp_path / "ledger.json").exists() or store.load().setups == []
    fake_client.quote.assert_not_called()
