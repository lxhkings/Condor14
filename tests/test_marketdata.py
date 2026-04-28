import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from data_source.marketdata import MarketDataClient, OptionLeg, Quote

FIXTURES = Path(__file__).parent / "fixtures" / "marketdata"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _mock_transport(mapping: dict[str, dict]) -> httpx.MockTransport:
    """`mapping` keys are URL path suffixes, values are the JSON to return."""
    def handler(request: httpx.Request) -> httpx.Response:
        for suffix, payload in mapping.items():
            if suffix in str(request.url):
                return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"s": "no_data"})
    return httpx.MockTransport(handler)


def test_quote_parses_response():
    transport = _mock_transport({"/v1/stocks/quotes/NVDA/": _load("quote_nvda.json")})
    client = MarketDataClient(api_key="test", transport=transport)
    q = client.quote("NVDA")
    assert isinstance(q, Quote)
    assert q.ticker == "NVDA"
    assert q.last == 216.61
    assert q.bid == 216.55
    assert q.ask == 216.65


def test_option_chain_parses_legs():
    transport = _mock_transport(
        {"/v1/options/chain/NVDA/": _load("option_chain_nvda.json")}
    )
    client = MarketDataClient(api_key="test", transport=transport)
    legs = client.option_chain("NVDA", expiration=date(2026, 5, 16))
    assert len(legs) == 4
    leg = next(L for L in legs if L.strike == 200.0 and L.side == "put")
    assert leg.bid == 1.85
    assert leg.ask == 1.95
    assert leg.open_interest == 2200
    assert leg.iv == 0.38


def test_daily_bars_parses_into_bar_rows():
    transport = _mock_transport(
        {"/v1/stocks/candles/D/NVDA/": _load("daily_bars_nvda.json")}
    )
    client = MarketDataClient(api_key="test", transport=transport)
    bars = client.daily_bars("NVDA", start=date(2025, 4, 25), end=date(2025, 5, 14))
    assert len(bars) == 20
    assert bars[0].ticker == "NVDA"
    assert bars[-1].close == 216.61


def test_no_data_response_raises():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"s": "no_data"})
    )
    client = MarketDataClient(api_key="test", transport=transport)
    with pytest.raises(RuntimeError, match="no_data"):
        client.quote("NVDA")


def test_http_error_raises():
    transport = httpx.MockTransport(lambda req: httpx.Response(500))
    client = MarketDataClient(api_key="test", transport=transport)
    with pytest.raises(httpx.HTTPStatusError):
        client.quote("NVDA")
