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

See `docs/superpowers/specs/2026-04-28-iron-condor-pseo-design.md` for
the full design.

## Math Engine

`math_engine/` is open-source and lives directly in this repo as the
E-E-A-T transparency anchor for this site (per spec §7.5):

  https://github.com/lxhkings/Condor14/tree/main/math_engine
