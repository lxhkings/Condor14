#!/bin/bash
# Run daily_run.py 30 minutes after US market open
# US market opens at 9:30 AM ET
# Summer (DST): 9:30 AM ET = 21:30 Beijing -> run at 22:00 Beijing
# Winter (EST): 9:30 AM ET = 22:30 Beijing -> run at 23:00 Beijing
# After pipeline: build site and push to git (triggers Vercel deploy)

set -e
cd /Users/xiaohongliang/projects/condor14

# Check if we're in US daylight saving time
# US DST: 2nd Sunday in March to 1st Sunday in November
is_dst() {
    /opt/homebrew/bin/uv run python -c "
import datetime
import pytz

et = pytz.timezone('America/New_York')
now = datetime.datetime.now(et)
# Check if currently in DST (et.dst() returns non-zero during DST)
print('yes' if now.dst() else 'no')
"
}

# Get current hour in Beijing time
BEIJING_HOUR=$(date +%H)

# Check DST
DST=$(is_dst)

# Only run if we're in the correct window:
# - Summer (DST): Beijing 22:30-23:59 (run at 22:30)
# - Winter (EST): Beijing 23:30-00:59 (run at 23:30)
BEIJING_MINUTE=$(date +%M)

if [ "$DST" = "yes" ]; then
    # Summer: should run at 22:30 Beijing
    if [ "$BEIJING_HOUR" -eq 22 ] && [ "$BEIJING_MINUTE" -ge 30 ]; then
        echo "Running pipeline (DST, 22:30+ Beijing = 10:30+ AM ET)"
        /opt/homebrew/bin/uv run python daily_run.py

        echo "Building site..."
        SITE_HOST=iron-condor-tracker.vercel.app /opt/homebrew/bin/uv run python build_site.py

        echo "Committing and pushing to git..."
        git add data/ledger.json public/
        git commit -m "data: $(date +%Y-%m-%d) setups [skip ci]" || echo "No changes to commit"
        git push origin main
    elif [ "$BEIJING_HOUR" -ge 23 ]; then
        echo "Running pipeline (DST, 23:xx Beijing = 11:xx AM ET)"
        /opt/homebrew/bin/uv run python daily_run.py

        echo "Building site..."
        SITE_HOST=iron-condor-tracker.vercel.app /opt/homebrew/bin/uv run python build_site.py

        echo "Committing and pushing to git..."
        git add data/ledger.json public/
        git commit -m "data: $(date +%Y-%m-%d) setups [skip ci]" || echo "No changes to commit"
        git push origin main
    else
        echo "Skipping: not in DST window (need 22:30+ Beijing, got ${BEIJING_HOUR}:${BEIJING_MINUTE})"
    fi
else
    # Winter: should run at 23:30 Beijing
    if [ "$BEIJING_HOUR" -eq 23 ] && [ "$BEIJING_MINUTE" -ge 30 ]; then
        echo "Running pipeline (EST, 23:30+ Beijing = 10:30+ AM ET)"
        /opt/homebrew/bin/uv run python daily_run.py

        echo "Building site..."
        SITE_HOST=iron-condor-tracker.vercel.app /opt/homebrew/bin/uv run python build_site.py

        echo "Committing and pushing to git..."
        git add data/ledger.json public/
        git commit -m "data: $(date +%Y-%m-%d) setups [skip ci]" || echo "No changes to commit"
        git push origin main
    elif [ "$BEIJING_HOUR" -ge 0 ] && [ "$BEIJING_HOUR" -lt 1 ]; then
        echo "Running pipeline (EST, 00:xx Beijing = 11:xx AM ET)"
        /opt/homebrew/bin/uv run python daily_run.py

        echo "Building site..."
        SITE_HOST=iron-condor-tracker.vercel.app /opt/homebrew/bin/uv run python build_site.py

        echo "Committing and pushing to git..."
        git add data/ledger.json public/
        git commit -m "data: $(date +%Y-%m-%d) setups [skip ci]" || echo "No changes to commit"
        git push origin main
    else
        echo "Skipping: not in EST window (need 23:30+ Beijing, got ${BEIJING_HOUR}:${BEIJING_MINUTE})"
    fi
fi
