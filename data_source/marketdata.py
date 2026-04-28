"""MarketData.app REST client.

Wraps the three endpoints used by the daily pipeline: quote, option chain,
historical daily bars. All HTTP calls go through one shared ``httpx.Client``
so tests can inject a ``MockTransport``.

Authentication: bearer token from ``MARKETDATA_API_KEY`` env var.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal

import httpx

from data_source.cache import BarRow

BASE_URL = "https://api.marketdata.app"


@dataclass(frozen=True)
class Quote:
    ticker: str
    last: float
    bid: float
    ask: float
    updated: datetime


@dataclass(frozen=True)
class OptionLeg:
    underlying: str
    expiration: date
    side: Literal["call", "put"]
    strike: float
    bid: float
    ask: float
    mid: float
    open_interest: int
    volume: int
    iv: float


def _ts_to_date(ts: int) -> date:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def _ts_to_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


class MarketDataClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 15.0,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("MARKETDATA_API_KEY")
        if not key:
            raise RuntimeError("MARKETDATA_API_KEY not set")
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MarketDataClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        body = resp.json()
        if body.get("s") != "ok":
            raise RuntimeError(f"MarketData {path} returned status: {body.get('s')}")
        return body

    def quote(self, ticker: str) -> Quote:
        body = self._get(f"/v1/stocks/quotes/{ticker}/")
        return Quote(
            ticker=body["symbol"][0],
            last=float(body["last"][0]),
            bid=float(body["bid"][0]),
            ask=float(body["ask"][0]),
            updated=_ts_to_dt(body["updated"][0]),
        )

    def option_chain(self, ticker: str, *, expiration: date) -> list[OptionLeg]:
        body = self._get(
            f"/v1/options/chain/{ticker}/",
            params={"expiration": expiration.isoformat()},
        )
        legs: list[OptionLeg] = []
        n = len(body["strike"])
        for i in range(n):
            legs.append(
                OptionLeg(
                    underlying=body["underlying"][i],
                    expiration=_ts_to_date(body["expiration"][i]),
                    side=body["side"][i],
                    strike=float(body["strike"][i]),
                    bid=float(body["bid"][i]),
                    ask=float(body["ask"][i]),
                    mid=float(body["mid"][i]),
                    open_interest=int(body["openInterest"][i]),
                    volume=int(body["volume"][i]),
                    iv=float(body["iv"][i]),
                )
            )
        return legs

    def daily_bars(
        self, ticker: str, *, start: date, end: date
    ) -> list[BarRow]:
        body = self._get(
            f"/v1/stocks/candles/D/{ticker}/",
            params={"from": start.isoformat(), "to": end.isoformat()},
        )
        rows: list[BarRow] = []
        for i in range(len(body["t"])):
            rows.append(
                BarRow(
                    ticker=ticker,
                    bar_date=_ts_to_date(body["t"][i]),
                    open=float(body["o"][i]),
                    high=float(body["h"][i]),
                    low=float(body["l"][i]),
                    close=float(body["c"][i]),
                    volume=int(body["v"][i]),
                )
            )
        return rows
