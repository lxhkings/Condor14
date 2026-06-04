"""Futu (富途) OpenD client for the daily iron-condor pipeline.

Uses futu-api to fetch market data through FutuOpenD.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal

from futu import KLType, RET_OK, OpenQuoteContext

from data_source.cache import BarRow
from data_source.rate_limit import TokenBucket

log = logging.getLogger(__name__)


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
    quote_collapsed: bool = False


# Futu 服务端限频提示常见关键字（中文/英文兜底）。
_RATE_LIMIT_KEYWORDS = ("频率", "rate limit", "FREQ_LIMIT", "请求频率")
_RATE_LIMIT_BACKOFF_SEC = 30.0


def _is_rate_limit_msg(msg: object) -> bool:
    s = str(msg)
    s_lower = s.lower()
    return any(
        (k.lower() in s_lower if k.isascii() else k in s)
        for k in _RATE_LIMIT_KEYWORDS
    )


def _to_code(ticker: str) -> str:
    return f"US.{ticker}"


def _exp_to_str(expiration: date) -> str:
    return expiration.strftime("%Y-%m-%d")


class FutuClient:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 11111,
        _ctx: OpenQuoteContext | None = None,
        chain_limiter: TokenBucket | None = None,
        exp_limiter: TokenBucket | None = None,
        snapshot_limiter: TokenBucket | None = None,
    ) -> None:
        if _ctx is not None:
            self._ctx = _ctx
        else:
            self._ctx = OpenQuoteContext(host=host, port=port)
        # Futu 公开限频：Qot_GetOptionChain & Qot_GetOptionExpirationDate 均为 10/30s。
        # 留 1 次安全余量 → 9/30s = 0.3 tok/s，capacity 9（允许冷启动突发 9 次）。
        self._chain_limiter = chain_limiter or TokenBucket(rate_per_sec=0.3, capacity=9)
        self._exp_limiter = exp_limiter or TokenBucket(rate_per_sec=0.3, capacity=9)
        # Futu 公开限频：Qot_GetMarketSnapshot 60/30s = 2/s。
        # 留 10% 安全余量 → 1.8/s，capacity=54。
        self._snapshot_limiter = snapshot_limiter or TokenBucket(rate_per_sec=1.8, capacity=54)

    def close(self) -> None:
        self._ctx.close()

    def __enter__(self) -> "FutuClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _safe_float(v: object, default: float = 0.0) -> float:
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
        if v is None:
            return default
        try:
            f = float(v)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return default
        if f != f:  # NaN
            return default
        return int(f)

    # ------------------------------------------------------------------
    def quote(self, ticker: str) -> Quote:
        self._snapshot_limiter.acquire()
        ret, data = self._ctx.get_market_snapshot([_to_code(ticker)])
        if ret != RET_OK or data.empty:
            return Quote(
                ticker=ticker,
                last=0.0,
                bid=0.0,
                ask=0.0,
                updated=datetime.now(timezone.utc),
            )
        row = data.iloc[0]
        return Quote(
            ticker=ticker,
            last=self._safe_float(row.get("last_price")),
            bid=self._safe_float(row.get("bid_price")),
            ask=self._safe_float(row.get("ask_price")),
            updated=datetime.now(timezone.utc),
        )

    def option_chain(
        self, ticker: str, *, expiration: date, near_spot: float | None = None
    ) -> list[OptionLeg]:
        code = _to_code(ticker)
        exp_str = _exp_to_str(expiration)

        self._chain_limiter.acquire()
        ret, chain = self._ctx.get_option_chain(code=code, start=exp_str, end=exp_str)
        if ret != RET_OK and _is_rate_limit_msg(chain):
            log.warning("rate-limited on get_option_chain(%s, %s); backing off %.0fs",
                        ticker, exp_str, _RATE_LIMIT_BACKOFF_SEC)
            time.sleep(_RATE_LIMIT_BACKOFF_SEC)
            self._chain_limiter.acquire()
            ret, chain = self._ctx.get_option_chain(code=code, start=exp_str, end=exp_str)
        if ret != RET_OK:
            log.warning("get_option_chain(%s, %s) failed: ret=%s msg=%s", ticker, exp_str, ret, chain)
            return []
        if chain.empty:
            log.warning("get_option_chain(%s, %s) returned empty DataFrame", ticker, exp_str)
            return []

        option_codes = chain["code"].tolist()

        # Split into batches of 200 (Futu limit)
        n_batches = (len(option_codes) + 199) // 200
        all_snapshots = []
        for i in range(0, len(option_codes), 200):
            batch = option_codes[i : i + 200]
            batch_num = i // 200 + 1
            self._snapshot_limiter.acquire()
            ret, snap = self._ctx.get_market_snapshot(batch)
            if ret != RET_OK and _is_rate_limit_msg(snap):
                log.warning(
                    "rate-limited on get_market_snapshot batch %d/%d for %s; backing off %.0fs",
                    batch_num, n_batches, ticker, _RATE_LIMIT_BACKOFF_SEC,
                )
                time.sleep(_RATE_LIMIT_BACKOFF_SEC)
                self._snapshot_limiter.acquire()
                ret, snap = self._ctx.get_market_snapshot(batch)
            if ret != RET_OK:
                log.warning(
                    "get_market_snapshot batch %d/%d for %s failed: ret=%s msg=%s",
                    batch_num, n_batches, ticker, ret, snap,
                )
                continue
            all_snapshots.append(snap)

        if not all_snapshots:
            return []

        import pandas as pd

        df = pd.concat(all_snapshots, ignore_index=True)

        # Filter to strikes near spot if requested
        if near_spot is not None and near_spot > 0:
            lo = near_spot * 0.70
            hi = near_spot * 1.30
            df = df[(df["option_strike_price"] >= lo) & (df["option_strike_price"] <= hi)]
            if df.empty:
                return []

        legs: list[OptionLeg] = []
        for _, row in df.iterrows():
            opt_type = row.get("option_type")
            if opt_type == "CALL":
                side = "call"
            elif opt_type == "PUT":
                side = "put"
            else:
                continue

            bid = self._safe_float(row.get("bid_price"))
            ask = self._safe_float(row.get("ask_price"))
            # Fair-value mid: prefer (bid+ask)/2, then last/prev-close,
            # then the lone quoted side.
            if bid > 0 and ask > 0:
                mid_raw = (bid + ask) / 2
            else:
                last = self._safe_float(row.get("last_price"))
                prev = self._safe_float(row.get("prev_close_price"))
                mid_raw = last if last > 0 else prev
                if mid_raw <= 0:
                    mid_raw = ask if ask > 0 else bid  # lone side
            # Use mid-price for backtesting when quotes are missing or
            # the spread is impractically wide (closed market).
            spread_ok = bid > 0 and ask > 0 and (ask - bid) / mid_raw <= 0.30 if mid_raw > 0 else False
            collapsed = False
            if mid_raw > 0 and not spread_ok:
                bid = round(mid_raw, 2)
                ask = round(mid_raw, 2)
                collapsed = True
            # Futu returns IV as percentage; convert to decimal for consistency
            iv = self._safe_float(row.get("option_implied_volatility")) / 100.0
            delta = self._safe_float(row.get("option_delta"))
            oi = self._safe_int(row.get("option_open_interest"))
            vol = self._safe_int(row.get("volume"))

            # Drop legs with zero pricing data (nothing to estimate from).
            if bid <= 0 and ask <= 0:
                continue

            legs.append(
                OptionLeg(
                    underlying=ticker,
                    expiration=expiration,
                    side=side,
                    strike=float(row["option_strike_price"]),
                    bid=bid,
                    ask=ask,
                    mid=(bid + ask) / 2,
                    open_interest=oi,
                    volume=vol,
                    iv=iv,
                    delta=delta,
                    quote_collapsed=collapsed,
                )
            )
        return legs

    def daily_bars(
        self, ticker: str, *, start: date, end: date
    ) -> list[BarRow]:
        code = _to_code(ticker)
        ret, data, _ = self._ctx.request_history_kline(
            code=code,
            ktype=KLType.K_DAY,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            max_count=200,
        )
        if ret != RET_OK or data.empty:
            return []

        rows: list[BarRow] = []
        for _, row in data.iterrows():
            time_key = row["time_key"]
            if isinstance(time_key, datetime):
                d = time_key.date()
            else:
                d = datetime.strptime(str(time_key)[:10], "%Y-%m-%d").date()
            if start <= d <= end:
                rows.append(
                    BarRow(
                        ticker=ticker,
                        bar_date=d,
                        open=self._safe_float(row.get("open")),
                        high=self._safe_float(row.get("high")),
                        low=self._safe_float(row.get("low")),
                        close=self._safe_float(row.get("close")),
                        volume=self._safe_int(row.get("volume")),
                    )
                )
        return rows

    def list_expirations(self, ticker: str) -> list[date]:
        code = _to_code(ticker)
        self._exp_limiter.acquire()
        ret, data = self._ctx.get_option_expiration_date(code=code)
        if ret != RET_OK and _is_rate_limit_msg(data):
            log.warning("rate-limited on get_option_expiration_date(%s); backing off %.0fs",
                        ticker, _RATE_LIMIT_BACKOFF_SEC)
            time.sleep(_RATE_LIMIT_BACKOFF_SEC)
            self._exp_limiter.acquire()
            ret, data = self._ctx.get_option_expiration_date(code=code)
        if ret != RET_OK:
            log.warning("get_option_expiration_date(%s) failed: ret=%s msg=%s", ticker, ret, data)
            return []
        if data.empty:
            log.warning("get_option_expiration_date(%s) returned empty DataFrame", ticker)
            return []

        date_col = "strike_time" if "strike_time" in data.columns else "expiry_date"
        dates: set[date] = set()
        for val in data[date_col]:
            d = datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
            dates.add(d)
        return sorted(dates)
