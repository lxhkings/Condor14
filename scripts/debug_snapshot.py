"""Debug FutuClient option_chain flow step by step."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from futu import OpenQuoteContext, RET_OK
import pandas as pd

TICKERS = ["COIN", "GLD", "SPY"]

def main():
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

    for ticker in TICKERS:
        code = f"US.{ticker}"
        print(f"\n=== {ticker} ===")

        # Step 1: Get expirations
        ret, exp_data = ctx.get_option_expiration_date(code=code)
        if ret != RET_OK:
            continue
        exp_str = str(exp_data.iloc[0]['strike_time'])[:10]

        # Step 2: Get option chain (option codes)
        ret, chain = ctx.get_option_chain(code=code, start=exp_str, end=exp_str)
        if ret != RET_OK or chain.empty:
            continue
        option_codes = chain["code"].tolist()
        print(f"  chain codes: {len(option_codes)}")

        # Step 3: Get market snapshot for first batch (max 200)
        batch = option_codes[:5]  # Just test 5 codes
        ret, snap = ctx.get_market_snapshot(batch)
        print(f"  snapshot ret={ret}, rows={len(snap) if ret == RET_OK else 'N/A'}")
        if ret == RET_OK and not snap.empty:
            print(f"  columns: {snap.columns.tolist()}")
            for _, row in snap.iterrows():
                opt_type = row.get('option_type', 'N/A')
                strike = row.get('option_strike_price', 'N/A')
                bid = row.get('bid_price', 'N/A')
                ask = row.get('ask_price', 'N/A')
                iv = row.get('option_implied_volatility', 'N/A')
                oi = row.get('option_open_interest', 'N/A')
                print(f"    {opt_type} strike={strike}: bid={bid}, ask={ask}, iv={iv}, oi={oi}")

    ctx.close()

if __name__ == "__main__":
    main()