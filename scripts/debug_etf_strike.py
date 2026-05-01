"""Debug ETF strike picker issue."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from data_source.futu_client import FutuClient
from math_engine.expiration import pick_expiration

ETFs = ["SPY", "QQQ", "IWM", "SMH"]

def main():
    with FutuClient() as client:
        for ticker in ETFs:
            q = client.quote(ticker)
            exps = client.list_expirations(ticker)

            # What pick_expiration would choose
            try:
                chosen = pick_expiration(today=date.today(), available=exps)
            except Exception as e:
                print(f"{ticker}: pick_expiration failed - {e}")
                continue

            print(f"\n=== {ticker} (last={q.last:.2f}) ===")
            print(f"  pick_expiration chose: {chosen}")
            print(f"  available expirations (next 5): {sorted([e for e in exps if e >= date.today()])[:5]}")

            # Get chain for chosen expiry
            chain = client.option_chain(ticker, expiration=chosen, near_spot=q.last)
            print(f"  chain count for chosen expiry: {len(chain)}")

            if chain:
                calls = sorted({L.strike for L in chain if L.side == "call"})
                puts = sorted({L.strike for L in chain if L.side == "put"})
                print(f"  call strikes: {calls[:5]}...{calls[-3:] if len(calls)>5 else ''}")
                print(f"  put strikes: {puts[:5]}...{puts[-3:] if len(puts)>5 else ''}")
            else:
                # Try without near_spot filter
                chain_full = client.option_chain(ticker, expiration=chosen, near_spot=None)
                print(f"  chain count (no filter): {len(chain_full)}")
                if chain_full:
                    strikes = sorted(set(L.strike for L in chain_full))
                    print(f"  all strikes: min={min(strikes)}, max={max(strikes)}")

if __name__ == "__main__":
    main()