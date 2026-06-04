# Iron Condor PSEO — Data Pipeline

Daily pipeline that maintains `data/ledger.json` with real Iron Condor
setups computed from MarketData OPRA quotes.

## Required GitHub Secret

- `MARKETDATA_API_KEY` — get from https://www.marketdata.app/

## Manual run

```
uv sync
MARKETDATA_API_KEY=xxx uv run python daily_run.py
```

## Scheduled run (local, macOS launchd)

The nightly pipeline runs on the local Mac via a launchd LaunchAgent
(weekdays 22:30 Beijing / 14:30 UTC). launchd is used instead of plain
`crontab` because crontab jobs run without keychain access, so the
`osxkeychain` git credential helper returns nothing and the push fails with
`could not read Username`. A LaunchAgent runs in the logged-in GUI session
where the keychain is unlocked, so the push authenticates.

Install:

```
cp scripts/com.condor14.daily.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.condor14.daily.plist
```

The Mac must be logged in and awake at 22:30 for the run to fire and push.

See `docs/superpowers/specs/2026-04-28-iron-condor-pseo-design.md` for
the full design.

