"""Test option chain for SPY/QQQ/IWM on multiple medium-term expirations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from data_source.futu_client import FutuClient

ETFs = ["SPY", "QQQ", "IWM"]
WINDOW_EXPIRATIONS = [date(2026, 5, 12), date(2026, 5, 13), date(2026, 5, 15)]

def main():
    with FutuClient() as client:
        for ticker in ETFs:
            q = client.quote(ticker)
            print(f"\n=== {ticker} (last={q.last:.2f}) ===")

            for exp in WINDOW_EXPIRATIONS:
                chain = client.option_chain(ticker, expiration=exp, near_spot=q.last)
                if chain:
                    strikes = sorted(set(L.strike for L in chain))
                    print(f"  {exp}: chain={len(chain)}, strikes [{min(strikes)}-{max(strikes)}]")
                else:
                    # Try without near_spot
                    chain_full = client.option_chain(ticker, expiration=exp, near_spot=None)
                    print(f"  {exp}: chain=0 (near_spot), full={len(chain_full)}")

if __name__ == "__main__":
    main()