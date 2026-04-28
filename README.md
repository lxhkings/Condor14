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

## Math Engine Open-Source Mirror

`math_engine/` is mirrored to a public read-only repository as the
E-E-A-T transparency anchor for this site (per spec §7.5):

  https://github.com/lxhkings/iron-condor-math-engine

### Bootstrap (one-time, manual)

```bash
# In a fresh clone of this repo:
git subtree split --prefix=math_engine -b math-engine-only
git remote add mirror git@github.com:lxhkings/iron-condor-math-engine.git
git push --force mirror math-engine-only:main

# Then in the public repo, manually add:
#   LICENSE (MIT)
#   README.md  (link back to this repo for full pipeline context)
```

### Recurring sync

`.github/workflows/mirror_math_engine.yml` runs on every push to `main` whose
diff touches `stock/math_engine/**`. Daily `chore(data):` commits do not match
the path filter and therefore do not trigger the mirror.

### Required secret

`MIRROR_DEPLOY_KEY`: SSH private key whose public half is registered as a
deploy key with WRITE access on `iron-condor-math-engine`. Generate with
`ssh-keygen -t ed25519 -f mirror_deploy -C "math-engine-mirror"`, register
the `.pub` half on the public repo (Settings → Deploy keys → Add → Allow write),
and paste the private half into this repo's Settings → Secrets → Actions.
