"""Daily pipeline orchestrator.

Step order per design spec §2:
    1. Trading-day guard (exit 0 if non-trading)
    2. For each ticker in TICKERS: open new setup or log skip
    3. For all open setups: append daily_mark and settle if expired
    4. Persist ledger atomically

Network calls are encapsulated in `IBKRClient`. Pure functions live in
`math_engine/`. State lives in `ledger.json`.
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config import SECTORS, TICKERS
from data_source.cache import BarRow, DailyBarsCache
from data_source.futu_client import FutuClient, OptionLeg
from data_source.trading_calendar import is_trading_day
from ledger.schema import (
    DailyMark,
    Ledger,
    Settlement,
    Setup,
    SkippedEntry,
)
from ledger.store import LedgerStore
from math_engine.atr import atr14
from math_engine.expiration import NoSuitableExpirationError, pick_expiration
from math_engine.iron_condor import (
    IronCondor,
    ZeroOrNegativeCreditError,
    build_condor,
)
from math_engine.liquidity import leg_passes_liquidity
from math_engine.pnl_evaluator import evaluate_settlement
from math_engine.sma import classify_trend_bias, sma
from math_engine.strike_picker import NoValidIronCondorError, pick_strikes

log = logging.getLogger("daily_run")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def list_expirations(client: FutuClient, ticker: str) -> list[date]:
    """Wrapper used by tests to monkeypatch expiration listing."""
    return client.list_expirations(ticker)


def _refresh_bars(
    client: FutuClient, cache: DailyBarsCache, ticker: str, today: date
) -> list[BarRow]:
    """Ensure we have at least 30 bars ending today; refresh from MarketData if stale."""
    latest = cache.latest_date(ticker)
    if latest is None or latest < today - timedelta(days=2):
        start = today - timedelta(days=60)
        bars = client.daily_bars(ticker, start=start, end=today)
        cache.upsert(bars)
    return cache.read(ticker, start=today - timedelta(days=60), end=today)


def _open_one_setup(
    *,
    client: FutuClient,
    cache: DailyBarsCache,
    ticker: str,
    today: date,
) -> Setup | SkippedEntry:
    bars = _refresh_bars(client, cache, ticker, today)
    if len(bars) < 21:
        return SkippedEntry(ticker=ticker, date=today, reason="insufficient_history")

    high_low_close = [(b.high, b.low, b.close) for b in bars]
    closes = [b.close for b in bars]

    atr_value = atr14(high_low_close)
    sma_value = sma(closes, period=20)
    quote = client.quote(ticker)
    # Fall back to latest bar close when live quote is unavailable (e.g. no
    # market-data subscription). This is safe — daily bar close is at most one
    # day stale and ATR-anchored wings are wide enough to absorb that drift.
    spot = quote.last if quote.last > 0 else closes[-1]
    bias = classify_trend_bias(close=spot, sma=sma_value)

    expirations = list_expirations(client, ticker)
    # Try all expirations in 13-16 day window, sorted by distance from 14 days
    window_exps = []
    for exp in expirations:
        days = (exp - today).days
        if 13 <= days <= 16:
            window_exps.append((abs(days - 14), exp))
    if not window_exps:
        return SkippedEntry(ticker=ticker, date=today, reason="no_expiration_in_window")
    window_exps.sort()  # Prefer closest to 14 days

    # Try each expiration until we find one with data
    chosen_expiry = None
    chain = None
    for _, exp in window_exps:
        candidate_chain = client.option_chain(ticker, expiration=exp, near_spot=spot)
        if candidate_chain:
            chosen_expiry = exp
            chain = candidate_chain
            break

    if chosen_expiry is None or chain is None:
        return SkippedEntry(ticker=ticker, date=today, reason="empty_chain_all_window_expirations")

    available_calls = sorted({L.strike for L in chain if L.side == "call"})
    available_puts = sorted({L.strike for L in chain if L.side == "put"})
    available = sorted(set(available_calls) | set(available_puts))
    try:
        sc, lc, sp, lp = pick_strikes(spot=spot, atr14=atr_value,
                                      available_strikes=available)
    except NoValidIronCondorError as e:
        return SkippedEntry(ticker=ticker, date=today, reason=f"strike_pick_failed:{e}")

    def _find(strike: float, side: str) -> OptionLeg | None:
        for L in chain:
            if L.side == side and abs(L.strike - strike) < 1e-9:
                return L
        return None

    legs = {
        "short_call": _find(sc, "call"),
        "long_call":  _find(lc, "call"),
        "short_put":  _find(sp, "put"),
        "long_put":   _find(lp, "put"),
    }
    for name, leg in legs.items():
        if leg is None:
            return SkippedEntry(ticker=ticker, date=today, reason=f"missing_leg:{name}")
        rejection = leg_passes_liquidity(leg)
        if rejection is not None:
            return SkippedEntry(ticker=ticker, date=today,
                                reason=f"illiquid:{name}:{rejection.value}")

    try:
        ic: IronCondor = build_condor(**legs)
    except ZeroOrNegativeCreditError as e:
        return SkippedEntry(ticker=ticker, date=today, reason=f"no_credit:{e}")

    target_exit = today + timedelta(days=14)
    return Setup(
        id=f"{ticker}-{today.isoformat()}",
        ticker=ticker,
        sector=SECTORS.get(ticker, "Unknown"),
        start_date=today,
        target_exit_date=target_exit,
        expiry_used=chosen_expiry,
        underlying_at_open=spot,
        atr14_at_open=round(atr_value, 4),
        sma20_at_open=round(sma_value, 4),
        iv_percentile_at_open=50,  # placeholder; full IV-rank in Plan B
        trend_bias=bias,
        short_call_strike=ic.short_call.strike,
        long_call_strike=ic.long_call.strike,
        short_put_strike=ic.short_put.strike,
        long_put_strike=ic.long_put.strike,
        net_credit_at_open=ic.net_credit,
        wing_width=ic.wing_width,
        max_profit=ic.max_profit,
        max_loss=ic.max_loss,
        break_even_upper=ic.break_even_upper,
        break_even_lower=ic.break_even_lower,
        status="open",
        daily_marks=[],
        settlement=None,
    )


def _evaluate_open_setups(
    *,
    ledger: Ledger,
    client: FutuClient,
    cache: DailyBarsCache,
    today: date,
) -> None:
    for i, s in enumerate(ledger.setups):
        if s.status != "open":
            continue
        quote = client.quote(s.ticker)
        # Fall back to latest bar close when live quote is unavailable
        bars = cache.read(s.ticker, start=today - timedelta(days=5), end=today)
        spot = quote.last if quote.last > 0 else (bars[-1].close if bars else 0.0)
        breached = (
            spot < s.short_put_strike or spot > s.short_call_strike
        )
        new_marks = s.daily_marks + [
            DailyMark(date=today, underlying_close=spot, breached_short=breached)
        ]
        if today >= s.target_exit_date:
            settlement_outcome = evaluate_settlement(
                underlying_close=spot,
                short_call=s.short_call_strike,
                short_put=s.short_put_strike,
                wing_width=s.wing_width,
                net_credit=s.net_credit_at_open,
            )
            settled = Settlement(
                settled_on=today,
                final_underlying=spot,
                breached_side=settlement_outcome.breached_side,
                final_pnl_per_spread=settlement_outcome.final_pnl_per_spread,
            )
            ledger.setups[i] = Setup(
                **{**s.__dict__,
                   "status": settlement_outcome.status,
                   "daily_marks": new_marks,
                   "settlement": settled},
            )
            if ledger.first_settlement_date is None:
                ledger.first_settlement_date = today
        else:
            ledger.setups[i] = Setup(**{**s.__dict__, "daily_marks": new_marks})


def run(
    *,
    today: date,
    client: FutuClient,
    store: LedgerStore,
    cache_path: Path,
) -> int:
    if not is_trading_day(today):
        log.info("not a trading day, exiting")
        return 0

    ledger = store.load()
    if ledger.site_launch_date is None:
        ledger.site_launch_date = today

    cache = DailyBarsCache(cache_path)

    _evaluate_open_setups(ledger=ledger, client=client, cache=cache, today=today)

    for ticker in TICKERS:
        if any(s.ticker == ticker and s.start_date == today for s in ledger.setups):
            log.info("skipped %s: already have a setup for today", ticker)
            continue
        result = _open_one_setup(client=client, cache=cache, ticker=ticker, today=today)
        if isinstance(result, Setup):
            ledger.setups.append(result)
            log.info("opened setup %s", result.id)
        else:
            ledger.skipped.append(result)
            log.info("skipped %s: %s", result.ticker, result.reason)

    ledger.last_run = datetime.now(timezone.utc)
    store.save(ledger)
    return 0


def main() -> int:
    here = Path(__file__).parent
    today = datetime.now().date()
    with FutuClient() as client:
        store = LedgerStore(here / "data" / "ledger.json")
        return run(today=today, client=client, store=store,
                   cache_path=here / "data" / "cache.sqlite")


if __name__ == "__main__":
    sys.exit(main())
