"""Test without near_spot filter."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from data_source.futu_client import FutuClient

TICKERS = ["COIN", "GLD", "JPM", "SPY"]

def main():
    with FutuClient() as client:
        for ticker in TICKERS:
            q = client.quote(ticker)
            exps = client.list_expirations(ticker)
            suitable = sorted([e for e in exps if e >= date.today()])[:1]
            exp = suitable[0]

            # Test WITHOUT near_spot filter
            chain_full = client.option_chain(ticker, expiration=exp, near_spot=None)
            # Test WITH near_spot filter
            chain_near = client.option_chain(ticker, expiration=exp, near_spot=q.last)

            print(f"\n=== {ticker} (last={q.last:.2f}, exp={exp}) ===")
            print(f"  full chain (no filter): {len(chain_full)} legs")
            print(f"  near_spot filter: {len(chain_near)} legs")

            if chain_near:
                print(f"  Sample legs in near_spot range:")
                for leg in chain_near[:3]:
                    print(f"    {leg.side} {leg.strike}: bid={leg.bid}, ask={leg.ask}, OI={leg.open_interest}")
            elif chain_full:
                print(f"  ALL legs are outside near_spot range ({q.last:.2f} ±30%)")
                strikes = sorted(set(l.strike for l in chain_full))
                print(f"  Available strikes: min={min(strikes)}, max={max(strikes)}")

if __name__ == "__main__":
    main()