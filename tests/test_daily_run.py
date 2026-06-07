from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from data_source.cache import BarRow, ExpirationsCache
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
                  raw_bid=1.05, raw_ask=1.15, open_interest=1500, **base),
        OptionLeg(side="put",  strike=200.0, bid=1.85, ask=1.95, mid=1.90,
                  raw_bid=1.85, raw_ask=1.95, open_interest=2000, **base),
        OptionLeg(side="call", strike=230.0, bid=2.10, ask=2.20, mid=2.15,
                  raw_bid=2.10, raw_ask=2.20, open_interest=2500, **base),
        OptionLeg(side="call", strike=235.0, bid=1.20, ask=1.30, mid=1.25,
                  raw_bid=1.20, raw_ask=1.30, open_interest=1800, **base),
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
                        lambda client, ticker, **kw: [date(2026, 5, 12)])
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
                        lambda client, ticker, **kw: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", [])  # don't open new setups
    monkeypatch.setattr("daily_run.SECTORS", {})

    # Seed an open setup whose target_exit_date is today
    seed_open = Setup(
        id="NVDA-2026-04-14", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 14), target_exit_date=date(2026, 4, 28),
        expiry_used=date(2026, 4, 30),
        underlying_at_open=210.0, atr14_at_open=4.0, sma20_at_open=200.0,
        vol_percentile_at_open=50, trend_bias="bullish",
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
                        lambda client, ticker, **kw: [date(2026, 5, 12)])
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


def test_list_expirations_wrapper_returns_cached_value_without_calling_client(tmp_path):
    from daily_run import list_expirations as wrap

    cache = ExpirationsCache(tmp_path / "cache.sqlite")
    cache.put("AAPL", fetched_on=date(2026, 5, 9),
              expirations=[date(2026, 5, 23)])
    client = MagicMock()
    result = wrap(client, "AAPL", cache=cache, today=date(2026, 5, 9))
    assert result == [date(2026, 5, 23)]
    client.list_expirations.assert_not_called()


def test_list_expirations_wrapper_fetches_and_caches_on_miss(tmp_path):
    from daily_run import list_expirations as wrap

    cache = ExpirationsCache(tmp_path / "cache.sqlite")
    client = MagicMock()
    client.list_expirations.return_value = [date(2026, 5, 23), date(2026, 5, 30)]
    result = wrap(client, "AAPL", cache=cache, today=date(2026, 5, 9))
    assert result == [date(2026, 5, 23), date(2026, 5, 30)]
    client.list_expirations.assert_called_once_with("AAPL")
    # 二次调用走缓存
    client.list_expirations.reset_mock()
    again = wrap(client, "AAPL", cache=cache, today=date(2026, 5, 9))
    assert again == result
    client.list_expirations.assert_not_called()


def test_list_expirations_wrapper_does_not_cache_empty_result(tmp_path):
    from daily_run import list_expirations as wrap

    cache = ExpirationsCache(tmp_path / "cache.sqlite")
    client = MagicMock()
    client.list_expirations.return_value = []
    wrap(client, "AAPL", cache=cache, today=date(2026, 5, 9))
    # 第二次仍然要打 client，因为空结果不缓存（可能是 transient error）
    wrap(client, "AAPL", cache=cache, today=date(2026, 5, 9))
    assert client.list_expirations.call_count == 2


def test_list_expirations_wrapper_backwards_compat_no_cache_arg():
    """旧测试：不传 cache/today 时仍直接转发给 client。"""
    from daily_run import list_expirations as wrap

    client = MagicMock()
    client.list_expirations.return_value = [date(2026, 5, 23)]
    assert wrap(client, "AAPL") == [date(2026, 5, 23)]


def test_open_setup_captures_analytics(tmp_path, fake_client, monkeypatch):
    from daily_run import run
    from dataclasses import replace

    base_legs = _legs(expiration=date(2026, 5, 12))
    fake_client.option_chain.return_value = [
        replace(L, code=f"US.NVDA-{L.side}-{int(L.strike)}") for L in base_legs
    ]
    fake_client.option_exercise_prob.return_value = 7.0
    from data_source.futu_client import VolPoint
    fake_client.option_volatility.return_value = [
        VolPoint(date=date(2026, 5, 11), iv=40.0, hv=28.0),
        VolPoint(date=date(2026, 5, 12), iv=42.0, hv=30.0),
    ]

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations", lambda client, ticker, **kw: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", ["NVDA"])
    monkeypatch.setattr("daily_run.SECTORS", {"NVDA": "Semiconductors"})

    store = LedgerStore(tmp_path / "ledger.json")
    run(today=date(2026, 4, 28), client=fake_client, store=store, cache_path=tmp_path / "cache.sqlite")

    snap = store.load().setups[0].analytics_at_open
    assert snap is not None
    assert snap.implied_pop == 86.0          # 100 - 7 - 7
    assert snap.short_call_iv == 42.0        # latest VolPoint
    assert snap.iv_gt_hv is True


def test_open_setup_analytics_none_on_api_failure(tmp_path, fake_client, monkeypatch):
    from daily_run import run
    fake_client.option_exercise_prob.return_value = None  # API failed
    fake_client.option_volatility.return_value = None

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations", lambda client, ticker, **kw: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", ["NVDA"])
    monkeypatch.setattr("daily_run.SECTORS", {"NVDA": "Semiconductors"})

    store = LedgerStore(tmp_path / "ledger.json")
    run(today=date(2026, 4, 28), client=fake_client, store=store, cache_path=tmp_path / "cache.sqlite")

    out = store.load()
    assert len(out.setups) == 1               # setup still opens
    assert out.setups[0].analytics_at_open is None


def test_run_populates_vol_percentile_and_atr60(tmp_path, fake_client, monkeypatch):
    from datetime import timedelta

    from daily_run import run
    from math_engine.atr import atr60
    from math_engine.volatility import vol_percentile

    # 280 calm bars ending 2026-04-28: gentle drift, constant 4.0 range.
    end = date(2026, 4, 28)
    n = 280
    long_bars = []
    price = 200.0
    for i in range(n):
        d = end - timedelta(days=(n - 1 - i))
        long_bars.append(BarRow(
            ticker="NVDA", bar_date=d,
            open=price, high=price + 2.0, low=price - 2.0,
            close=price + 0.5, volume=1_000_000,
        ))
        price += 0.05
    fake_client.daily_bars.return_value = long_bars

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations",
                        lambda client, ticker, **kw: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", ["NVDA"])
    monkeypatch.setattr("daily_run.SECTORS", {"NVDA": "Semiconductors"})

    store = LedgerStore(tmp_path / "ledger.json")
    run(today=end, client=fake_client, store=store, cache_path=tmp_path / "cache.sqlite")

    s = store.load().setups[0]

    # Recompute expectations from the same bars.
    hlc = [(b.high, b.low, b.close) for b in long_bars]
    closes = [b.close for b in long_bars]
    assert s.atr60_at_open == pytest.approx(round(atr60(hlc), 4))
    assert s.atr60_at_open > 0.0
    assert s.vol_percentile_at_open == vol_percentile(closes)


def test_mark_dedupes_quote_per_ticker(tmp_path, fake_client, monkeypatch):
    from daily_run import run
    from ledger.schema import Ledger

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.TICKERS", [])   # 不开新仓
    monkeypatch.setattr("daily_run.SECTORS", {})

    def _open(idx: int) -> Setup:
        return Setup(
            id=f"NVDA-2026-04-2{idx}", ticker="NVDA", sector="Semiconductors",
            start_date=date(2026, 4, 20), target_exit_date=date(2026, 5, 12),
            expiry_used=date(2026, 5, 12),
            underlying_at_open=210.0, atr14_at_open=4.0, sma20_at_open=200.0,
            vol_percentile_at_open=50, trend_bias="bullish",
            short_call_strike=230.0, long_call_strike=235.0,
            short_put_strike=200.0, long_put_strike=195.0,
            net_credit_at_open=1.50, wing_width=5.0,
            max_profit=1.50, max_loss=3.50,
            break_even_upper=231.50, break_even_lower=198.50,
            status="open", daily_marks=[], settlement=None,
        )

    store = LedgerStore(tmp_path / "ledger.json")
    store.save(Ledger(setups=[_open(1), _open(2), _open(3)],
                       site_launch_date=date(2026, 4, 20)))

    run(today=date(2026, 4, 28), client=fake_client, store=store,
        cache_path=tmp_path / "cache.sqlite")

    # 3 个同标 open setup → quote 只取一次
    assert fake_client.quote.call_count == 1
    # 每个 setup 仍各自追加了当日 mark
    out = store.load()
    assert all(len(s.daily_marks) == 1 for s in out.setups)


def test_run_attaches_quote_audit(tmp_path, fake_client, monkeypatch):
    from daily_run import run

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations",
                        lambda client, ticker, **kw: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", ["NVDA"])
    monkeypatch.setattr("daily_run.SECTORS", {"NVDA": "Semiconductors"})

    store = LedgerStore(tmp_path / "ledger.json")
    cache_path = tmp_path / "cache.sqlite"
    run(today=date(2026, 4, 28), client=fake_client, store=store, cache_path=cache_path)

    qa = store.load().setups[0].quote_audit
    assert qa is not None
    assert set(qa.legs) == {"short_call", "long_call", "short_put", "long_put"}
    # raw==bid/ask -> 保守等于发布，deviation 0
    assert qa.net_credit_conservative == qa.net_credit_published
    assert qa.credit_deviation == 0.0
    assert qa.any_collapsed is False
