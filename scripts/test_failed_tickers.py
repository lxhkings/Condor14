"""Deep dive test for tickers with empty chains."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from data_source.futu_client import FutuClient

# Tickers that failed
FAILED = ["COIN", "MSTR", "MARA", "PLTR", "ARM", "HOOD", "GLD", "SLV", "TLT", "JPM", "DIS", "XLE"]

def main():
    with FutuClient() as client:
        for ticker in FAILED:
            q = client.quote(ticker)
            exps = client.list_expirations(ticker)
            print(f"\n=== {ticker} (last={q.last:.2f}, expirations={len(exps)}) ===")
            # Test first 3 available expirations
            suitable = sorted([e for e in exps if e >= date.today()])[:3]
            for exp in suitable:
                chain = client.option_chain(ticker, expiration=exp, near_spot=q.last if q.last > 0 else 100)
                print(f"  exp={exp.isoformat()}: chain_count={len(chain)}")
                if chain:
                    # Show first 2 legs
                    for leg in chain[:2]:
                        print(f"    {leg.side} {leg.strike}: bid={leg.bid}, ask={leg.ask}, OI={leg.open_interest}")

if __name__ == "__main__":
    main()