"""IBKR (Interactive Brokers) client for the daily iron-condor pipeline.

Uses ib_insync to fetch delayed market data through TWS/IB Gateway.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal

from ib_insync import IB, Option, Stock

from data_source.cache import BarRow


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
    delta: float = 0.0


class IBKRClient:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 4001,
        client_id: int = 1,
        _ib: IB | None = None,
    ) -> None:
        if _ib is not None:
            self._ib = _ib
        else:
            self._ib = IB()
            self._ib.connect(host, port, clientId=client_id)
            self._ib.reqMarketDataType(3)  # delayed data — no subscription needed
        self._con_id_cache: dict[str, int] = {}
        self._chains_cache: dict[str, list] = {}

    def close(self) -> None:
        self._ib.disconnect()

    def __enter__(self) -> "IBKRClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    def _ensure_stock_qualified(self, ticker: str) -> int:
        if ticker in self._con_id_cache:
            return self._con_id_cache[ticker]
        cd = Stock(ticker, "SMART", "USD")
        self._ib.qualifyContracts(cd)
        self._con_id_cache[ticker] = cd.conId
        return cd.conId

    def _get_chains(self, ticker: str) -> list:
        if ticker in self._chains_cache:
            return self._chains_cache[ticker]
        con_id = self._ensure_stock_qualified(ticker)
        chains = self._ib.reqSecDefOptParams(ticker, "", "STK", con_id)
        self._chains_cache[ticker] = chains
        return chains

    # ------------------------------------------------------------------
    @staticmethod
    def _safe_float(v: object, default: float = 0.0) -> float:
        """Float conversion that survives None, NaN, and Inf."""
        if v is None:
            return default
        try:
            f = float(v)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return default
        if f != f:  # NaN
            return default
        return f

    @staticmethod
    def _safe_int(v: object, default: int = 0) -> int:
        """Int conversion that survives None, NaN, and Inf."""
        if v is None:
            return default
        try:
            f = float(v)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return default
        if f != f:  # NaN
            return default
        return int(f)

    @staticmethod
    def _valid_price(v: object) -> float | None:
        """Return the price as a positive float, or None if missing/NaN/zero."""
        if v is None:
            return None
        f = float(v)  # type: ignore[arg-type]
        if f != f:    # NaN guard
            return None
        return f if f > 0 else None

    def quote(self, ticker: str) -> Quote:
        self._ensure_stock_qualified(ticker)
        cd = Stock(ticker, "SMART", "USD")
        self._ib.reqMarketDataType(3)
        t = self._ib.reqTickers(cd)[0]
        lp = self._valid_price(t.last)
        cp = self._valid_price(t.close)
        return Quote(
            ticker=ticker,
            last=lp if lp is not None else (cp if cp is not None else 0.0),
            bid=self._safe_float(t.bid),
            ask=self._safe_float(t.ask),
            updated=datetime.now(timezone.utc),
        )

    def option_chain(
        self, ticker: str, *, expiration: date, near_spot: float | None = None
    ) -> list[OptionLeg]:
        chains = self._get_chains(ticker)
        exp_str = expiration.strftime("%Y%m%d")

        # Prefer SMART exchange, then search all chains for the expiration
        smart_chain = next((c for c in chains if c.exchange == "SMART"), None)
        ordered = [smart_chain] if smart_chain is not None else []
        ordered += [c for c in chains if c is not smart_chain]

        all_strikes: list[float] = []
        for chain in ordered:
            if exp_str in chain.expirations:
                all_strikes = [float(s) for s in chain.strikes if float(s) >= 5.0]
                break

        if not all_strikes:
            return []

        if near_spot is not None and near_spot > 0:
            lo = near_spot * 0.70
            hi = near_spot * 1.30
            strikes = [s for s in all_strikes if lo <= s <= hi]
            if not strikes:
                strikes = all_strikes
        else:
            strikes = all_strikes

        contracts = []
        for strike in strikes:
            contracts.append(Option(ticker, exp_str, strike, "C", "SMART"))
            contracts.append(Option(ticker, exp_str, strike, "P", "SMART"))

        # Batch qualify first (handles pacing internally), fall back to
        # one-by-one when some strikes are not listed for this expiration.
        try:
            self._ib.qualifyContracts(*contracts)
            valid = [c for c in contracts if c.conId > 0]
        except ValueError:
            valid = []
            for c in contracts:
                try:
                    self._ib.qualifyContracts(c)
                    if c.conId > 0:
                        valid.append(c)
                except ValueError:
                    pass
                self._ib.sleep(0.05)

        if not valid:
            return []

        self._ib.reqMarketDataType(4)  # frozen data — looser permission requirements
        tickers = self._ib.reqTickers(*valid)

        legs: list[OptionLeg] = []
        for t in tickers:
            side = t.contract.right
            bid = self._safe_float(t.bid)
            ask = self._safe_float(t.ask)
            iv = 0.0
            delta = 0.0
            if t.modelGreeks is not None:
                iv = self._safe_float(t.modelGreeks.impliedVol)
                delta = self._safe_float(t.modelGreeks.delta)
            oi = 0
            if side == "P":
                oi = self._safe_int(t.putOpenInterest)
            elif side == "C":
                oi = self._safe_int(t.callOpenInterest)
            legs.append(
                OptionLeg(
                    underlying=ticker,
                    expiration=expiration,
                    side="call" if side == "C" else "put",
                    strike=self._safe_float(t.contract.strike),
                    bid=bid,
                    ask=ask,
                    mid=(bid + ask) / 2,
                    open_interest=oi,
                    volume=self._safe_int(t.volume),
                    iv=iv,
                    delta=delta,
                )
            )
        return legs

    def daily_bars(
        self, ticker: str, *, start: date, end: date
    ) -> list[BarRow]:
        self._ensure_stock_qualified(ticker)
        cd = Stock(ticker, "SMART", "USD")
        duration_days = (end - start).days + 5
        bars = self._ib.reqHistoricalData(
            cd,
            endDateTime="",
            durationStr=f"{duration_days} D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
        )
        rows: list = []
        for bar in bars:
            d: date
            if isinstance(bar.date, datetime):
                d = bar.date.date()
            else:
                d = bar.date
            if start <= d <= end:
                rows.append(
                    BarRow(
                        ticker=ticker,
                        bar_date=d,
                        open=float(bar.open),
                        high=float(bar.high),
                        low=float(bar.low),
                        close=float(bar.close),
                        volume=int(bar.volume),
                    )
                )
        return rows

    def list_expirations(self, ticker: str) -> list[date]:
        chains = self._get_chains(ticker)
        dates: set[date] = set()
        for chain in chains:
            for exp in chain.expirations:
                dates.add(datetime.strptime(exp, "%Y%m%d").date())
        return sorted(dates)
