#!/bin/bash
# Daily pipeline: fetch options data → build site → push → Vercel deploys.
# Run at 14:30 UTC (10:30 AM ET DST / 09:30 AM ET EST) Mon-Fri via crontab.
set -euo pipefail

REPO=/Users/xiaohongliang/projects/condor14
LOG=$REPO/logs/daily.log
mkdir -p "$REPO/logs"
exec >> "$LOG" 2>&1

export https_proxy=http://127.0.0.1:10808
export http_proxy=http://127.0.0.1:10808

echo "=== $(date -u '+%Y-%m-%d %H:%M:%S UTC') start ==="

cd "$REPO"

# Skip non-trading days
/opt/homebrew/bin/uv run python - <<'EOF'
from data_source.trading_calendar import is_trading_day
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
et_today = datetime.now(ZoneInfo("America/New_York")).date()
if not is_trading_day(et_today):
    print(f"Not a trading day ({et_today}), skipping.")
    sys.exit(1)
EOF
status=$?
[ $status -ne 0 ] && echo "Skipped." && exit 0

echo "--- daily_run.py ---"
/opt/homebrew/bin/uv run python daily_run.py

echo "--- build_site.py ---"
SITE_HOST=www.condor14.com /opt/homebrew/bin/uv run python build_site.py

echo "--- git commit & push ---"
git add data/ledger.json data/cache.sqlite data/last_indexed.json public/
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    git commit -m "chore(site): daily update $(date -u +%Y-%m-%d)"
    git pull --rebase origin main
    git push origin main
    echo "Pushed. Vercel will deploy."
fi

echo "=== done ==="
