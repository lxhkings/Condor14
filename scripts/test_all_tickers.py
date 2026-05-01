"""Test all tickers across multiple expirations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from data_source.futu_client import FutuClient

# All candidates
CANDIDATES = [
    # ETFs
    ("SPY", "Broad ETF"), ("QQQ", "Broad ETF"), ("IWM", "Broad ETF"),
    ("SMH", "Sector ETF"), ("ARKK", "Sector ETF"),
    # Semiconductors (已有 NVDA/TSLA)
    ("AMD", "Semiconductors"), ("AVGO", "Semiconductors"), ("ASML", "Semiconductors"), ("TSM", "Semiconductors"),
    # Mega-Cap Tech (已有 AAPL/AMZN/MSFT/META/GOOGL)
    ("NFLX", "Mega-Cap Tech"),
    # Crypto/Hot
    ("COIN", "Crypto"), ("MSTR", "Crypto"), ("MARA", "Crypto"),
    ("PLTR", "Hot Tech"), ("ARM", "Hot Tech"), ("HOOD", "Hot Tech"),
    # Hedge/Finance
    ("GLD", "Hedge"), ("SLV", "Hedge"), ("TLT", "Hedge"),
    ("JPM", "Finance"), ("DIS", "Finance"), ("XLE", "Sector ETF"),
]

def main():
    print("Testing tickers across multiple expirations...")
    print("=" * 90)

    working = []
    partial = []
    failed = []

    with FutuClient() as client:
        for ticker, category in CANDIDATES:
            q = client.quote(ticker)
            exps = client.list_expirations(ticker)
            if not exps:
                failed.append((ticker, "no expirations"))
                continue

            # Test first 3 expirations
            suitable = sorted([e for e in exps if e >= date.today()])[:3]
            results = []
            for exp in suitable:
                chain = client.option_chain(ticker, expiration=exp, near_spot=q.last if q.last > 0 else 100)
                results.append((exp, len(chain)))

            max_chain = max(r[1] for r in results)
            if max_chain > 0:
                working.append((ticker, category, q.last, results))
            elif q.last > 0:
                partial.append((ticker, category, q.last, "quote OK but all chains empty"))
            else:
                failed.append((ticker, "no quote data"))

    # Print working tickers
    print("\n=== WORKING (has option chain data) ===")
    for ticker, cat, last, results in working:
        exp_strs = [f"{r[0]}:{r[1]}" for r in results]
        print(f"{ticker:6} [{cat:12}] last={last:.2f} | {', '.join(exp_strs)}")

    # Print partial (quote OK but no chain)
    if partial:
        print("\n=== PARTIAL (quote OK, chain empty) ===")
        for ticker, cat, last, reason in partial:
            print(f"{ticker:6} [{cat:12}] last={last:.2f} | {reason}")

    # Print failed
    if failed:
        print("\n=== FAILED ===")
        for ticker, reason in failed:
            print(f"{ticker:6} | {reason}")

    print(f"\nSummary: {len(working)} working, {len(partial)} partial, {len(failed)} failed")

if __name__ == "__main__":
    main()