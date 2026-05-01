#!/bin/bash
# Run daily_run.py 30 minutes after US market open
# US market opens at 9:30 AM ET
# Summer (DST): 9:30 AM ET = 21:30 Beijing -> run at 22:00 Beijing
# Winter (EST): 9:30 AM ET = 22:30 Beijing -> run at 23:00 Beijing

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
# - Summer (DST): Beijing 22:00-22:30
# - Winter (EST): Beijing 23:00-23:30
if [ "$DST" = "yes" ]; then
    # Summer: should run at 22:00 Beijing
    if [ "$BEIJING_HOUR" -ge 22 ] && [ "$BEIJING_HOUR" -lt 23 ]; then
        echo "Running pipeline (DST, 22:xx Beijing = 10:xx AM ET)"
        /opt/homebrew/bin/uv run python daily_run.py
    else
        echo "Skipping: not in DST window (need 22:xx Beijing, got ${BEIJING_HOUR}:xx)"
    fi
else
    # Winter: should run at 23:00 Beijing
    if [ "$BEIJING_HOUR" -ge 23 ]; then
        echo "Running pipeline (EST, 23:xx Beijing = 10:xx AM ET)"
        /opt/homebrew/bin/uv run python daily_run.py
    else
        echo "Skipping: not in EST window (need 23:xx Beijing, got ${BEIJING_HOUR}:xx)"
    fi
fi
