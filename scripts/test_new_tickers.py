"""Test data availability for new tickers.

Usage: uv run python scripts/test_new_tickers.py
Requires: FutuOpenD running at 127.0.0.1:11111
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, datetime
from data_source.futu_client import FutuClient

# Candidates from user's table
CANDIDATES = [
    # 宽基/板块 ETF
    ("SPY", "Broad ETF"),
    ("QQQ", "Broad ETF"),
    ("IWM", "Broad ETF"),
    ("SMH", "Sector ETF"),
    ("ARKK", "Sector ETF"),
    # 核心科技龙头 (已有: NVDA, TSLA, AAPL, AMZN, MSFT, META, GOOGL)
    ("AMD", "Semiconductors"),
    ("NFLX", "Mega-Cap Tech"),
    ("AVGO", "Semiconductors"),
    ("ASML", "Semiconductors"),
    ("TSM", "Semiconductors"),  # TSMC 在 Futu 可能是 TSM
    # 高波动/热门股
    ("COIN", "Crypto"),
    ("MSTR", "Crypto"),
    ("MARA", "Crypto"),
    ("PLTR", "Hot Tech"),
    ("ARM", "Hot Tech"),
    ("HOOD", "Hot Tech"),
    # 金融/避险/能源
    ("GLD", "Hedge"),
    ("SLV", "Hedge"),
    ("TLT", "Hedge"),
    ("JPM", "Finance"),
    ("DIS", "Finance"),
    ("XLE", "Sector ETF"),
]

def test_ticker(client: FutuClient, ticker: str) -> dict:
    """Test quote, expirations, and option chain for a ticker."""
    result = {"ticker": ticker, "quote": None, "expirations": None, "chain": None, "error": None}

    try:
        q = client.quote(ticker)
        result["quote"] = {"last": q.last, "bid": q.bid, "ask": q.ask}
    except Exception as e:
        result["error"] = f"quote failed: {e}"
        return result

    try:
        exps = client.list_expirations(ticker)
        result["expirations"] = len(exps) if exps else 0
        if not exps:
            result["error"] = "no expirations"
            return result
        # Test nearest expiration (within 20 days)
        today = date.today()
        suitable = sorted([e for e in exps if e >= today and (e - today).days <= 20])
        if not suitable:
            suitable = sorted([e for e in exps if e >= today])
        nearest = suitable[0]
        spot = q.last if q.last > 0 else 100
        chain = client.option_chain(ticker, expiration=nearest, near_spot=spot)
        result["chain"] = len(chain) if chain else 0
        result["nearest_exp"] = nearest.isoformat()
        if chain == 0:
            result["error"] = f"empty chain for exp={nearest}"
    except Exception as e:
        result["error"] = f"chain failed: {e}"

    return result

def main():
    print("Testing new tickers data availability...")
    print("=" * 80)

    with FutuClient() as client:
        for ticker, category in CANDIDATES:
            r = test_ticker(client, ticker)
            status = "OK" if r["chain"] and r["chain"] > 0 else f"FAIL: {r['error']}"
            quote_str = f"last={r['quote']['last']:.2f}" if r["quote"] else "N/A"
            exp_str = f"exp={r['expirations']}" if r["expirations"] else "N/A"
            chain_str = f"chain={r['chain']}" if r["chain"] is not None else "N/A"
            nearest_str = f"nearest={r.get('nearest_exp', 'N/A')}"
            print(f"{ticker:6} [{category:12}] {status:30} | {quote_str:15} | {exp_str:6} | {chain_str:6} | {nearest_str}")

if __name__ == "__main__":
    main()