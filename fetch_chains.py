"""Fetch and cache full option chain data for all configured tickers.

Usage:
    uv run python fetch_chains.py            # all tickers, today
    uv run python fetch_chains.py AAPL MSFT  # specific tickers
"""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from config import TICKERS
from data_source.cache import ExpirationsCache, OptionChainCache
from data_source.futu_client import FutuClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fetch_chains")

CACHE_PATH = Path("data/cache.sqlite")
MAX_EXPIRY_DAYS = 90  # 只抓 90 天内到期日，避免拉太多远月数据


def run(tickers: list[str], today: date) -> None:
    chain_cache = OptionChainCache(CACHE_PATH)
    exp_cache = ExpirationsCache(CACHE_PATH)

    with FutuClient() as client:
        for ticker in tickers:
            # 获取到期日列表（优先走缓存）
            expirations = exp_cache.get(ticker, fetched_on=today)
            if expirations is None:
                expirations = client.list_expirations(ticker)
                if expirations:
                    exp_cache.put(ticker, fetched_on=today, expirations=expirations)

            if not expirations:
                log.warning("%s: no expirations found, skipping", ticker)
                continue

            cutoff = today + timedelta(days=MAX_EXPIRY_DAYS)
            expirations = [e for e in expirations if e <= cutoff]
            log.info("%s: %d expirations within %d days", ticker, len(expirations), MAX_EXPIRY_DAYS)

            for exp in expirations:
                if chain_cache.has(ticker, exp, today):
                    log.info("%s %s: already cached, skipping", ticker, exp)
                    continue

                legs = client.option_chain(ticker, expiration=exp)
                if legs:
                    chain_cache.put(ticker, exp, today, legs)
                    log.info("%s %s: saved %d legs", ticker, exp, len(legs))
                else:
                    log.warning("%s %s: empty chain", ticker, exp)


if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else TICKERS
    today = date.today()
    log.info("Fetching option chains for %d tickers (today=%s)", len(tickers), today)
    run(tickers, today)
    log.info("Done.")
