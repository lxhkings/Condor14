from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from data_source.futu_client import FutuClient, OptionLeg, Quote


def _make_stock_snapshot(*, last: float = 100.0, bid: float = 99.0, ask: float = 101.0) -> pd.DataFrame:
    return pd.DataFrame([{
        "last_price": last,
        "bid_price": bid,
        "ask_price": ask,
    }])


def _make_option_snapshot(strikes_and_types: list[tuple[float, str, float, float, float, float, int, int]]) -> pd.DataFrame:
    rows = []
    for strike, opt_type, bid, ask, iv, delta, oi, vol in strikes_and_types:
        rows.append({
            "option_strike_price": strike,
            "option_type": opt_type,
            "bid_price": bid,
            "ask_price": ask,
            "option_implied_volatility": iv,
            "option_delta": delta,
            "option_open_interest": oi,
            "volume": vol,
        })
    return pd.DataFrame(rows)


def _make_bar_df(dates_and_prices: list[tuple[date, float, float, float, float, float]]) -> pd.DataFrame:
    rows = []
    for d, o, h, l, c, v in dates_and_prices:
        rows.append({
            "time_key": datetime(d.year, d.month, d.day),
            "open": o, "high": h, "low": l, "close": c, "volume": v,
        })
    return pd.DataFrame(rows)


class TestQuote:
    def test_quote_parses_response(self):
        mock_ctx = MagicMock()
        mock_ctx.get_market_snapshot.return_value = (0, _make_stock_snapshot(
            last=216.61, bid=216.55, ask=216.65,
        ))
        client = FutuClient(_ctx=mock_ctx)
        q = client.quote("NVDA")
        assert isinstance(q, Quote)
        assert q.ticker == "NVDA"
        assert q.last == 216.61
        assert q.bid == 216.55
        assert q.ask == 216.65


class TestOptionChain:
    def test_option_chain_parses_legs(self):
        mock_ctx = MagicMock()
        mock_ctx.get_option_chain.return_value = (
            0,
            pd.DataFrame([{"code": f"US.NVDA260516{side}{int(s*1000):08d}"}
                          for s, side in [(195, "P"), (200, "P"), (230, "C"), (235, "C")]]),
        )
        mock_ctx.get_market_snapshot.return_value = (
            0,
            _make_option_snapshot([
                (195.0, "PUT",  1.05, 1.15, 40.0, -0.70, 1500, 100),
                (200.0, "PUT",  1.85, 1.95, 38.0, -0.50, 2200, 200),
                (230.0, "CALL", 2.10, 2.20, 42.0,  0.55, 2500, 150),
                (235.0, "CALL", 1.20, 1.30, 39.0,  0.35, 1800, 50),
            ]),
        )
        client = FutuClient(_ctx=mock_ctx)

        result = client.option_chain("NVDA", expiration=date(2026, 5, 16))
        assert len(result) == 4
        leg = next(L for L in result if L.strike == 200.0 and L.side == "put")
        assert leg.bid == 1.85
        assert leg.ask == 1.95
        assert leg.open_interest == 2200
        assert leg.iv == 0.38


class TestDailyBars:
    def test_daily_bars_parses_into_bar_rows(self):
        mock_ctx = MagicMock()
        mock_ctx.request_history_kline.return_value = (
            0,
            _make_bar_df([
                (date(2025, 4, 25), 200.0, 205.0, 198.0, 203.0, 1e6),
                (date(2025, 4, 28), 203.5, 208.0, 201.5, 206.5, 1.1e6),
                (date(2025, 4, 29), 207.0, 210.0, 205.0, 209.0, 1.2e6),
            ]),
            None,
        )
        client = FutuClient(_ctx=mock_ctx)

        result = client.daily_bars("NVDA", start=date(2025, 4, 25), end=date(2025, 4, 29))
        assert len(result) == 3
        assert result[0].ticker == "NVDA"
        assert result[-1].close == 209.0


class TestListExpirations:
    def test_list_expirations_deduplicates(self):
        mock_ctx = MagicMock()
        mock_ctx.get_option_expiration_date.return_value = (
            0,
            pd.DataFrame({"strike_time": ["2026-05-16", "2026-05-08", "2026-05-16", "2026-05-22"]}),
        )
        client = FutuClient(_ctx=mock_ctx)

        exps = client.list_expirations("NVDA")
        assert exps == [date(2026, 5, 8), date(2026, 5, 16), date(2026, 5, 22)]
