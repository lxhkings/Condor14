"""Debug Futu API raw response for option chain."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from futu import OpenQuoteContext, RET_OK

TICKERS = ["COIN", "GLD", "SPY"]  # Compare failing vs working

def main():
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

    for ticker in TICKERS:
        code = f"US.{ticker}"
        print(f"\n=== {ticker} ({code}) ===")

        # Get expirations
        ret, exp_data = ctx.get_option_expiration_date(code=code)
        if ret != RET_OK:
            print(f"  expirations FAILED: {exp_data}")
            continue
        print(f"  expirations OK: columns={exp_data.columns.tolist()}")
        exp_str = str(exp_data.iloc[0]['strike_time'])[:10] if 'strike_time' in exp_data.columns else str(exp_data.iloc[0]['expiry_date'])[:10]
        print(f"  using exp={exp_str}")

        # Get option chain
        ret, chain = ctx.get_option_chain(code=code, start=exp_str, end=exp_str)
        if ret != RET_OK:
            print(f"  chain FAILED: {chain}")
            continue
        print(f"  chain OK: count={len(chain)}, columns={chain.columns.tolist()}")
        if len(chain) > 0:
            print(f"  first rows:")
            print(chain.head(3))

    ctx.close()

if __name__ == "__main__":
    main()