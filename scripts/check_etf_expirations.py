"""Check full expiration lists for ETFs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from data_source.futu_client import FutuClient

ETFs = ["SPY", "QQQ", "IWM", "SMH"]

def main():
    with FutuClient() as client:
        for ticker in ETFs:
            exps = client.list_expirations(ticker)
            today = date.today()

            print(f"\n=== {ticker} ===")
            print(f"  Total expirations: {len(exps)}")

            # Group by distance from today
            short = [e for e in exps if (e - today).days <= 7]
            medium = [e for e in exps if 8 <= (e - today).days <= 20]
            long = [e for e in exps if (e - today).days > 20]

            print(f"  Short (0-7 days): {len(short)} - {sorted(short)}")
            print(f"  Medium (8-20 days): {len(medium)} - {sorted(medium)}")
            print(f"  Long (>20 days): {len(long)}")

            # Check if there's a 13-16 day window
            window = [e for e in exps if 13 <= (e - today).days <= 16]
            if window:
                print(f"  In 13-16 day window: {sorted(window)}")
            else:
                print(f"  NO expiration in 13-16 day window!")

if __name__ == "__main__":
    main()