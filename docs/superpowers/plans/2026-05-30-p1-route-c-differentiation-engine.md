# P1 Route C — Differentiation Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded `iv_percentile=50` stub and the mis-passed `atr60=atr14` bug with real volatility data so all 9 spintax templates become reachable and same-bias ticker pages stop sharing verbatim prose; inject per-ticker Track Record into the prose.

**Architecture:** Two new pure-math functions (realized-volatility percentile, atr60) feed two new `Setup` data points. `daily_run` computes them at open; `build_site` passes them into the existing spintax `render_prelude`, which already selects templates by `(trend_bias, vol_bucket)` and injects a `vol_regime` modifier. A schema field rename (`iv_percentile_at_open` → `vol_percentile_at_open`) keeps the data model honest (we display realized, not implied, volatility).

**Tech Stack:** Python 3.13, `uv`, pytest, Jinja2 templates, frozen dataclasses + JSON ledger.

**Spec:** `docs/superpowers/specs/2026-05-30-p1-route-c-differentiation-engine-design.md`

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `math_engine/volatility.py` | `realized_vol`, `vol_percentile` — pure functions, no I/O | Create |
| `tests/test_volatility.py` | Unit tests for the above | Create |
| `math_engine/atr.py` | add `atr60` alongside `atr14` | Modify |
| `tests/test_atr.py` | add atr60 cases | Modify |
| `ledger/schema.py` | add `atr60_at_open` field (default), rename `iv_percentile_at_open`→`vol_percentile_at_open`, back-compat deserialize | Modify |
| `content_engine/spintax.py` | rename `classify_iv_percentile`→`classify_vol_percentile`; read `vol_percentile_at_open`; add optional `track_record` param | Modify |
| `daily_run.py` | widen bar window; compute `atr60`+`vol_percentile`; set new Setup fields | Modify |
| `build_site.py` | pass real `atr60` and `track_record` into `render_prelude` | Modify |
| `content_engine/templates/spintax/*.md.j2` (9) | `Implied`→`Realized` wording; new variable name | Modify |
| `content_engine/templates/spintax/_track_record_line.md.j2` | shared Track Record sentence partial | Create |
| All `tests/*` constructing `Setup(...)` | rename `iv_percentile_at_open`→`vol_percentile_at_open` | Modify (sed) |

**Phasing (verify before adding cost):**
- **Phase 1 — unlock engine:** Tasks 1–6 (real HV percentile, real atr60, schema rename, wiring, wording).
- **Phase 2 — inject uniqueness:** Task 7 (Track Record prose line).
- **Phase 3 — measure → maybe expand:** Task 8 (re-audit duplication; only write template variants if still high). No speculative prose before measuring.

---

## Task 1: Realized-volatility percentile (`math_engine/volatility.py`)

**Files:**
- Create: `math_engine/volatility.py`
- Test: `tests/test_volatility.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_volatility.py`:

```python
import math

import pytest

from math_engine.volatility import realized_vol, vol_percentile


def test_realized_vol_flat_series_is_zero():
    closes = [100.0] * 25
    assert realized_vol(closes, window=20) == pytest.approx(0.0)


def test_realized_vol_known_alternating_series():
    # Alternating +1%/-1% log-ish moves give a positive, finite annualized vol.
    closes = [100.0]
    for i in range(1, 25):
        closes.append(closes[-1] * (1.01 if i % 2 else 1 / 1.01))
    v = realized_vol(closes, window=20)
    assert v > 0.0
    assert math.isfinite(v)


def test_realized_vol_too_few_closes_raises():
    with pytest.raises(ValueError):
        realized_vol([100.0, 101.0], window=20)


def test_vol_percentile_high_when_latest_window_most_volatile():
    # Calm for a long lookback, then a violent last 20 days -> high percentile.
    calm = [100.0 + 0.01 * i for i in range(260)]
    violent = []
    price = calm[-1]
    for i in range(20):
        price *= 1.08 if i % 2 else 1 / 1.08
        violent.append(price)
    closes = calm + violent
    assert vol_percentile(closes, window=20, lookback=252) >= 90


def test_vol_percentile_low_when_latest_window_calmest():
    violent = [100.0]
    for i in range(260):
        violent.append(violent[-1] * (1.05 if i % 2 else 1 / 1.05))
    calm = [violent[-1] + 0.001 * i for i in range(20)]
    closes = violent + calm
    assert vol_percentile(closes, window=20, lookback=252) <= 10


def test_vol_percentile_insufficient_history_returns_50():
    assert vol_percentile([100.0] * 25, window=20, lookback=252) == 50
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_volatility.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'math_engine.volatility'`

- [ ] **Step 3: Write the implementation**

Create `math_engine/volatility.py`:

```python
"""Realized (historical) volatility and its trailing percentile.

Pure functions, no I/O. Used to bucket spintax prose by a *real* volatility
reading instead of a hardcoded placeholder. This is realized (backward-looking)
volatility — page copy must say "realized", not "implied".
"""

import math
from typing import Sequence

TRADING_DAYS_PER_YEAR = 252
MIN_RANK_SAMPLE = 30  # minimum rolling-vol observations before ranking is meaningful


def realized_vol(closes: Sequence[float], window: int = 20) -> float:
    """Annualized realized volatility over the last `window` daily closes.

    = sample stdev of the last `window` daily log returns * sqrt(252).
    Requires at least `window + 1` closes (to form `window` returns).
    """
    if len(closes) < window + 1:
        raise ValueError(
            f"realized_vol needs at least {window + 1} closes, got {len(closes)}"
        )
    rets = [
        math.log(closes[i] / closes[i - 1])
        for i in range(len(closes) - window, len(closes))
    ]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(TRADING_DAYS_PER_YEAR)


def vol_percentile(
    closes: Sequence[float], window: int = 20, lookback: int = 252
) -> int:
    """Percentile rank (0-100) of the latest realized vol vs its trailing
    distribution over `lookback` trading days.

    Builds the rolling `realized_vol` series across the trailing window and
    ranks the most recent value. If fewer than `window + MIN_RANK_SAMPLE`
    closes are available the distribution is too thin to rank, so we return
    50 (the neutral "medium" bucket) and the caller degrades gracefully.
    """
    if len(closes) < window + MIN_RANK_SAMPLE:
        return 50

    # One realized_vol observation per day where a full window is available,
    # capped to the lookback horizon.
    series = []
    start = max(window, len(closes) - lookback)
    for end in range(start, len(closes) + 1):
        series.append(realized_vol(closes[:end], window=window))

    latest = series[-1]
    below = sum(1 for v in series if v < latest)
    return round(100 * below / (len(series) - 1)) if len(series) > 1 else 50
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_volatility.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add math_engine/volatility.py tests/test_volatility.py
git commit -m "feat(math): add realized-vol percentile for spintax bucketing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: atr60 (`math_engine/atr.py`)

**Files:**
- Modify: `math_engine/atr.py`
- Test: `tests/test_atr.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_atr.py`:

```python
def test_atr60_needs_at_least_61_bars():
    import pytest

    from math_engine.atr import atr60

    bars = [(10.0, 9.0, 9.5)] * 60
    with pytest.raises(ValueError):
        atr60(bars)


def test_atr60_constant_range_equals_range():
    from math_engine.atr import atr60

    # 61 bars, each with a 1.0 high-low range and flat closes -> ATR == 1.0
    bars = [(10.0, 9.0, 9.5)] * 61
    assert atr60(bars) == pytest.approx(1.0)
```

(If `import pytest` is already at the top of `tests/test_atr.py`, drop the inline import in the first test.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_atr.py -k atr60 -v`
Expected: FAIL with `ImportError: cannot import name 'atr60'`

- [ ] **Step 3: Write the implementation**

In `math_engine/atr.py`, refactor `atr14` to delegate to a shared helper and add `atr60`. Replace the body of `atr14` (lines 19-44) with:

```python
def _atr(bars: Sequence[tuple[float, float, float]], period: int) -> float:
    """Wilder's ATR over `period` true ranges at the latest bar.

    `bars` = (high, low, close) tuples, oldest-to-newest. Needs `period + 1`
    bars (one anchor close + `period` TR observations).
    """
    if len(bars) < period + 1:
        raise ValueError(f"atr{period} needs at least {period + 1} bars, got {len(bars)}")

    trs: list[float] = []
    for i in range(1, len(bars)):
        high_t, low_t, _close_t = bars[i]
        prev_close = bars[i - 1][2]
        tr = max(
            high_t - low_t,
            abs(high_t - prev_close),
            abs(low_t - prev_close),
        )
        trs.append(tr)

    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def atr14(bars: Sequence[tuple[float, float, float]]) -> float:
    """Compute ATR14 (Wilder's) at the latest bar. Requires at least 15 bars."""
    return _atr(bars, 14)


def atr60(bars: Sequence[tuple[float, float, float]]) -> float:
    """Compute ATR60 (Wilder's) at the latest bar. Requires at least 61 bars."""
    return _atr(bars, 60)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_atr.py -v`
Expected: PASS (existing atr14 tests + 2 new atr60 tests)

- [ ] **Step 5: Commit**

```bash
git add math_engine/atr.py tests/test_atr.py
git commit -m "feat(math): add atr60 via shared Wilder helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Schema migration — add `atr60_at_open`, rename `iv_percentile_at_open`→`vol_percentile_at_open`

**Files:**
- Modify: `ledger/schema.py` (dataclass field lines 51-53; `ledger_from_json._setup` line ~145)
- Modify: `content_engine/spintax.py`
- Modify: `daily_run.py:176`
- Modify (sed sweep): `daily_run.py` + all `tests/*.py` that construct `Setup(...)`

- [ ] **Step 1: Edit the dataclass**

In `ledger/schema.py`, rename the field (currently line 53) and append the new defaulted field at the END of the `Setup` dataclass (after `settlement`). Default `0.0` keeps every existing test constructor valid and degrades `vol_regime` to "stable" for setups that predate the field.

Change line 53 `iv_percentile_at_open: int` → `vol_percentile_at_open: int`.

After the `settlement: Settlement | None` line, add:

```python
    atr60_at_open: float = 0.0
```

- [ ] **Step 2: Edit `ledger_from_json._setup` for back-compat**

In `ledger/schema.py`, in the `Setup(...)` returned by `_setup` (line ~145), replace:

```python
            iv_percentile_at_open=d["iv_percentile_at_open"],
```

with:

```python
            vol_percentile_at_open=d.get(
                "vol_percentile_at_open", d.get("iv_percentile_at_open", 50)
            ),
```

and add, alongside the other fields:

```python
            atr60_at_open=d.get("atr60_at_open", 0.0),
```

- [ ] **Step 3: Update spintax.py**

In `content_engine/spintax.py`:
- Rename `classify_iv_percentile` → `classify_vol_percentile` (line 19) and its call site (line 54).
- Line 54: `classify_vol_percentile(setup.vol_percentile_at_open)`.
- Line 63: change the template variable to `vol_percentile_at_open=setup.vol_percentile_at_open` (Task 6 renames it inside the templates).

- [ ] **Step 4: Update daily_run.py:176**

Change:

```python
        iv_percentile_at_open=50,  # placeholder; full IV-rank in Plan B
```

to (Task 4 fills the real value; for now keep it compiling):

```python
        vol_percentile_at_open=50,  # set to real value in this task's wiring (Task 4)
```

- [ ] **Step 5: Sed-rename remaining call sites**

Run this rename across `daily_run.py` and all tests (these are uniform keyword renames — there are 19 occurrences across the listed files):

```bash
grep -rl "iv_percentile_at_open" tests/ daily_run.py \
  | xargs sed -i '' 's/iv_percentile_at_open/vol_percentile_at_open/g'
```

Then verify nothing references the old name anywhere:

```bash
grep -rn "iv_percentile_at_open\|classify_iv_percentile" . --include='*.py' --include='*.j2'
```
Expected: no output.

- [ ] **Step 6: Add a legacy-ledger back-compat test**

Append to `tests/test_ledger_schema.py` (it already imports `ledger_from_json` / has `_setup`; mirror its style). This proves an old ledger written with the `iv_percentile_at_open` key and no `atr60_at_open` still deserializes:

```python
def test_from_json_reads_legacy_iv_key_and_missing_atr60():
    import json

    from ledger.schema import SCHEMA_VERSION, ledger_from_json

    s = _setup()  # existing helper -> a fully-populated Setup
    payload = {
        "schema_version": SCHEMA_VERSION,
        "site_launch_date": None, "first_settlement_date": None, "last_run": None,
        "skipped": [],
        "setups": [{
            "id": s.id, "ticker": s.ticker, "sector": s.sector,
            "start_date": s.start_date.isoformat(),
            "target_exit_date": s.target_exit_date.isoformat(),
            "expiry_used": s.expiry_used.isoformat(),
            "underlying_at_open": s.underlying_at_open,
            "atr14_at_open": s.atr14_at_open, "sma20_at_open": s.sma20_at_open,
            "iv_percentile_at_open": 73,  # legacy key, no vol_/atr60_ keys
            "trend_bias": s.trend_bias,
            "short_call_strike": s.short_call_strike, "long_call_strike": s.long_call_strike,
            "short_put_strike": s.short_put_strike, "long_put_strike": s.long_put_strike,
            "net_credit_at_open": s.net_credit_at_open, "wing_width": s.wing_width,
            "max_profit": s.max_profit, "max_loss": s.max_loss,
            "break_even_upper": s.break_even_upper, "break_even_lower": s.break_even_lower,
            "status": s.status, "daily_marks": [], "settlement": None,
        }],
    }
    out = ledger_from_json(json.dumps(payload))
    loaded = out.setups[0]
    assert loaded.vol_percentile_at_open == 73   # read from legacy iv key
    assert loaded.atr60_at_open == 0.0           # missing -> default
```

(If `_setup()` in this file requires args, pass the same ones its other tests use.)

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS (all existing tests green under the new field names; `atr60_at_open` defaults to 0.0 everywhere it isn't set).

- [ ] **Step 8: Commit**

```bash
git add ledger/schema.py content_engine/spintax.py daily_run.py tests/
git commit -m "refactor(schema): rename iv->vol percentile, add atr60_at_open

Field holds realized-vol percentile (honest naming). atr60_at_open is
additive with a 0.0 default; from_dict reads the legacy iv key so existing
ledgers deserialize unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Wire real values into `daily_run`

**Files:**
- Modify: `daily_run.py` (imports line ~33; `_refresh_bars` lines 71-81; setup build lines ~96 and ~176)
- Test: `tests/test_daily_run.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_daily_run.py`. It reuses the existing `fake_client` fixture and `run(...)` harness (same monkeypatch setup as `test_run_opens_a_setup_for_a_normal_ticker`), but overrides `client.daily_bars` to return ~280 gentle bars so `atr60` (needs 61) and `vol_percentile` (needs window+30) are computable. The bars keep a constant 4.0 high-low range (so `atr14` stays ~4.0 and strike-picking still finds the fixed fake legs), and we assert the new Setup fields equal values recomputed from the exact injected closes — deterministic, no fragile inequality:

```python
def test_run_populates_vol_percentile_and_atr60(tmp_path, fake_client, monkeypatch):
    from datetime import timedelta

    from daily_run import run
    from math_engine.atr import atr60
    from math_engine.volatility import vol_percentile

    # 280 calm bars ending 2026-04-28: gentle drift, constant 4.0 range.
    end = date(2026, 4, 28)
    n = 280
    long_bars = []
    price = 200.0
    for i in range(n):
        d = end - timedelta(days=(n - 1 - i))
        long_bars.append(BarRow(
            ticker="NVDA", bar_date=d,
            open=price, high=price + 2.0, low=price - 2.0,
            close=price + 0.5, volume=1_000_000,
        ))
        price += 0.05
    fake_client.daily_bars.return_value = long_bars

    monkeypatch.setattr("daily_run.is_trading_day", lambda d: True)
    monkeypatch.setattr("daily_run.list_expirations",
                        lambda client, ticker, **kw: [date(2026, 5, 12)])
    monkeypatch.setattr("daily_run.TICKERS", ["NVDA"])
    monkeypatch.setattr("daily_run.SECTORS", {"NVDA": "Semiconductors"})

    store = LedgerStore(tmp_path / "ledger.json")
    run(today=end, client=fake_client, store=store, cache_path=tmp_path / "cache.sqlite")

    s = store.load().setups[0]

    # Recompute expectations from the same bars the pipeline reads back (cache
    # read window is 400 days, so all 280 bars are in range).
    hlc = [(b.high, b.low, b.close) for b in long_bars]
    closes = [b.close for b in long_bars]
    assert s.atr60_at_open == pytest.approx(round(atr60(hlc), 4))
    assert s.atr60_at_open > 0.0
    assert s.vol_percentile_at_open == vol_percentile(closes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_daily_run.py::test_run_populates_vol_percentile_and_atr60 -v`
Expected: FAIL (setup still carries `vol_percentile_at_open == 50` and `atr60_at_open == 0.0`)

- [ ] **Step 3: Add imports**

In `daily_run.py` near line 33 (`from math_engine.atr import atr14`), change/add:

```python
from math_engine.atr import atr14, atr60
from math_engine.volatility import vol_percentile
```

- [ ] **Step 4: Widen the bar fetch window**

In `daily_run.py`, in `_refresh_bars` (lines 71-81), change both `timedelta(days=60)` occurrences to `timedelta(days=400)` so ~272 trading days are available for `vol_percentile(lookback=252)` and `atr60`:

```python
def _refresh_bars(
    client: FutuClient, cache: DailyBarsCache, ticker: str, today: date
) -> list[BarRow]:
    """Ensure ~1y of bars ending today; refresh from MarketData if stale."""
    latest = cache.latest_date(ticker)
    if latest is None or latest < today - timedelta(days=2):
        start = today - timedelta(days=400)
        bars = client.daily_bars(ticker, start=start, end=today)
        cache.upsert(bars)
    return cache.read(ticker, start=today - timedelta(days=400), end=today)
```

- [ ] **Step 5: Compute and set the values**

In `daily_run.py`, near line 96 where `atr_value`/`closes` are computed, add atr60 + percentile (guard atr60 when <61 bars):

```python
    atr_value = atr14(high_low_close)
    atr60_value = atr60(high_low_close) if len(high_low_close) >= 61 else 0.0
    vol_pct = vol_percentile(closes)
    sma_value = sma(closes, period=20)
```

Then in the `Setup(...)` constructor (the line edited in Task 3 Step 4), set the real values:

```python
        vol_percentile_at_open=vol_pct,
```

and add (next to `atr14_at_open=round(atr_value, 4),`):

```python
        atr60_at_open=round(atr60_value, 4),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_daily_run.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add daily_run.py tests/test_daily_run.py
git commit -m "feat(pipeline): compute real vol percentile + atr60 at open

Widen bar window to ~400 calendar days so 252-day percentile and atr60
are computable. Replaces the iv=50 placeholder.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Pass real atr60 into the prelude (`build_site.py`)

**Files:**
- Modify: `build_site.py:87`
- Test: `tests/test_build_site.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_build_site.py`. Construct two setups identical except for divergent atr14/atr60 and assert the rendered prelude gains the volatility-regime sentence (it is empty today because atr60 is mis-passed as atr14):

```python
def test_render_ticker_emits_vol_regime_sentence_when_atr_diverges(tmp_path):
    from build_site import _render_ticker
    # Reuse this module's existing _setup(...) helper; override atr fields so
    # atr14/atr60 ratio < 0.8 (contracting) -> modifier sentence non-empty.
    setup = _setup(ticker="SPY")  # existing helper in this file
    setup = dataclasses.replace(setup, atr14_at_open=2.0, atr60_at_open=4.0)
    html = _render_ticker(setup=setup, ledger=_ledger_with([setup]),
                          today=setup.start_date, env=_env(), base_url="https://x")
    assert "Volatility is contracting" in html
```

Adapt helper names (`_setup`, `_ledger_with`, `_env`) to whatever `tests/test_build_site.py` already defines; add `import dataclasses` at the top if missing.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_build_site.py::test_render_ticker_emits_vol_regime_sentence_when_atr_diverges -v`
Expected: FAIL (modifier empty because `atr60=setup.atr14_at_open` makes ratio 1.0)

- [ ] **Step 3: Fix the call**

In `build_site.py` lines 86-88, change:

```python
    prelude_md = render_prelude(
        setup=setup, atr60=setup.atr14_at_open, jinja_env=env,
    )
```

to:

```python
    prelude_md = render_prelude(
        setup=setup, atr60=setup.atr60_at_open, jinja_env=env,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_build_site.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add build_site.py tests/test_build_site.py
git commit -m "fix(site): pass real atr60 to prelude so vol_regime activates

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Prose wording — `Implied`→`Realized` across 9 spintax templates

**Files:**
- Modify: `content_engine/templates/spintax/{bullish,bearish,neutral}_{low,medium,high}.md.j2` (9 files)
- Test: `tests/test_spintax.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_spintax.py` (it already has a `_setup(*, trend_bias, iv=...)` helper — keyword renamed to `vol=` by Task 3's sed only if the param is literally `iv_percentile_at_open`; the local param `iv` stays, it just feeds `vol_percentile_at_open=`):

```python
def test_prelude_says_realized_not_implied():
    from content_engine.spintax import render_prelude
    env = _env()  # existing helper
    for bias in ("bullish", "bearish", "neutral"):
        for vol in (10, 50, 85):
            setup = _setup(trend_bias=bias, iv=vol)
            text = render_prelude(setup=setup, atr60=setup.atr14_at_open, jinja_env=env)
            assert "Realized volatility" in text
            assert "Implied volatility" not in text
            assert f"{vol}th percentile" in text
```

Adapt `_env()` to however `tests/test_spintax.py` builds its Jinja `Environment`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spintax.py::test_prelude_says_realized_not_implied -v`
Expected: FAIL ("Implied volatility" still present; `vol_percentile_at_open` variable not yet referenced in templates)

- [ ] **Step 3: Edit all 9 templates**

In each of the 9 `content_engine/templates/spintax/{bias}_{bucket}.md.j2` files, replace the sentence fragment:

```
Implied volatility registers at the {{ iv_percentile_at_open }}th percentile
```

with:

```
Realized volatility registers at the {{ vol_percentile_at_open }}th percentile
```

Apply with a sweep, then confirm:

```bash
sed -i '' \
  -e 's/Implied volatility registers at the {{ iv_percentile_at_open }}th percentile/Realized volatility registers at the {{ vol_percentile_at_open }}th percentile/' \
  content_engine/templates/spintax/*.md.j2
grep -rn "Implied volatility\|iv_percentile_at_open" content_engine/templates/spintax/
```
Expected grep output: empty.

(If wording differs slightly per file, edit each remaining match by hand until the grep is clean.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_spintax.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add content_engine/templates/spintax/ tests/test_spintax.py
git commit -m "feat(content): say realized (not implied) volatility in prelude

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Inject Track Record sentence into prose (Phase 2)

**Files:**
- Create: `content_engine/templates/spintax/_track_record_line.md.j2`
- Modify: `content_engine/spintax.py` (`render_prelude` signature + render context)
- Modify: `build_site.py:86-88` (pass `track_record`)
- Modify: 9 spintax bias templates (append the include)
- Test: `tests/test_spintax.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_spintax.py`:

```python
def test_prelude_includes_track_record_line_when_settled():
    from content_engine.spintax import render_prelude
    env = _env()
    setup = _setup(trend_bias="bullish", iv=50)
    tr = {"sample_size": 7, "win_rate": 0.57, "cumulative_pnl": 1.2,
          "worst_single_loss": -3.1, "max_drawdown": -4.0}
    text = render_prelude(setup=setup, atr60=setup.atr14_at_open,
                          jinja_env=env, track_record=tr)
    assert "7" in text
    assert "settled" in text.lower()


def test_prelude_omits_track_record_line_when_none_or_empty():
    from content_engine.spintax import render_prelude
    env = _env()
    setup = _setup(trend_bias="bullish", iv=50)
    none_text = render_prelude(setup=setup, atr60=setup.atr14_at_open,
                               jinja_env=env, track_record=None)
    zero_text = render_prelude(setup=setup, atr60=setup.atr14_at_open, jinja_env=env,
                               track_record={"sample_size": 0, "win_rate": None,
                                             "cumulative_pnl": 0.0,
                                             "worst_single_loss": 0.0,
                                             "max_drawdown": 0.0})
    assert "settled cycles" not in none_text.lower()
    assert "settled cycles" not in zero_text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_spintax.py -k track_record -v`
Expected: FAIL (`render_prelude() got an unexpected keyword argument 'track_record'`)

- [ ] **Step 3: Create the partial**

Create `content_engine/templates/spintax/_track_record_line.md.j2`:

```jinja
{% if track_record and track_record.sample_size and track_record.sample_size > 0 %} {{ ticker }}'s {{ track_record.sample_size }} prior settled cycles provide an empirical reference point for the strikes framed today.{% endif %}
```

- [ ] **Step 4: Update `render_prelude`**

In `content_engine/spintax.py`, change the signature (line 53) and pass `track_record` into the render context (line 58-64):

```python
def render_prelude(
    *, setup: Setup, atr60: float, jinja_env: Environment,
    track_record: dict | None = None,
) -> str:
    vol_bucket = classify_vol_percentile(setup.vol_percentile_at_open)
    regime = classify_vol_regime(atr14=setup.atr14_at_open, atr60=atr60)
    template_name = f"spintax/{setup.trend_bias}_{vol_bucket}.md.j2"
    template = jinja_env.get_template(template_name)
    return template.render(
        ticker=setup.ticker,
        underlying_at_open=setup.underlying_at_open,
        atr14_at_open=setup.atr14_at_open,
        sma20_at_open=setup.sma20_at_open,
        vol_percentile_at_open=setup.vol_percentile_at_open,
        vol_regime_modifier=_modifier_for(regime),
        track_record=track_record,
    )
```

- [ ] **Step 5: Append the include to all 9 bias templates**

At the END of each `content_engine/templates/spintax/{bias}_{bucket}.md.j2`, append:

```jinja
{% include 'spintax/_track_record_line.md.j2' %}
```

Apply + verify:

```bash
for f in content_engine/templates/spintax/{bullish,bearish,neutral}_{low,medium,high}.md.j2; do
  printf "\n{%% include 'spintax/_track_record_line.md.j2' %%}\n" >> "$f"
done
grep -L "_track_record_line" content_engine/templates/spintax/{bullish,bearish,neutral}_{low,medium,high}.md.j2
```
Expected last grep: empty (every bias template includes the partial).

- [ ] **Step 6: Wire `build_site` to pass it**

In `build_site.py` lines 86-88, change:

```python
    prelude_md = render_prelude(
        setup=setup, atr60=setup.atr60_at_open, jinja_env=env,
    )
```

to:

```python
    prelude_md = render_prelude(
        setup=setup, atr60=setup.atr60_at_open, jinja_env=env,
        track_record=track_record,
    )
```

(`track_record` is already a parameter of `_render_ticker` at line 84, populated from `alltime_stats` by the route-A wiring.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_spintax.py -v && uv run pytest tests/test_build_site.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add content_engine/spintax.py build_site.py content_engine/templates/spintax/ tests/test_spintax.py
git commit -m "feat(content): inject per-ticker track-record sentence into prelude

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Full verification + duplication re-audit (Phase 3 gate)

**Files:** none (measurement + decision only)

- [ ] **Step 1: Full suite + compliance**

Run: `uv run pytest -q`
Expected: all green.

- [ ] **Step 2: Rebuild and re-audit duplication**

Run: `uv run python build_site.py` then compare two same-bias tickers' prose:

```bash
for t in aapl tsla; do
  python3 -c "
import re
h=open('public/$t/index.html').read()
b=re.search(r'<body.*?>(.*)</body>',h,re.S).group(1)
b=re.sub(r'<style.*?</style>|<script.*?</script>','',b,flags=re.S)
b=re.sub(r'<[^>]+>',' ',b); b=re.sub(r'[ \t]+',' ',b)
print('\n'.join(l.strip() for l in b.splitlines() if l.strip())[:1200])
"
  echo "==========="
done
```

Expected: the AAPL and TSLA intro paragraphs now differ (different `Nth percentile`, possibly different bucket, and a per-ticker Track Record sentence) — no longer verbatim identical.

- [ ] **Step 3: Decide on Task C-6 (template-pool expansion)**

If same-bucket tickers (same `trend_bias` AND same low/medium/high bucket) still produce near-verbatim intros, write 1-2 phrasing variants per template selected by `zlib.crc32(ticker.encode()) % N` in `render_prelude`. Otherwise **skip C-6** — the spec defers it precisely so we don't write speculative prose. Record the decision in the commit message / a short note.

- [ ] **Step 4: Commit the rebuilt site**

```bash
git add public/
git commit -m "chore(site): rebuild with activated differentiation engine

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes for the implementer

- Run `uv run pytest -q` after every task — the schema rename (Task 3) touches many files; the suite is the safety net.
- `daily_run.py` needs FutuOpenD running only for a live run; all tasks here are unit-tested with fakes and do not require the gateway. Do **not** run `daily_run.py` as part of implementation.
- Compliance check runs inside `build_site.py` (exits 2 on banned "hypothetical"-class language). "Realized volatility" is descriptive and allowed; if the build exits 2, read the reported line — it will name the offending phrase.
- The `atr60_at_open` default of `0.0` is intentional: it makes `classify_vol_regime` return "stable" for any setup lacking a real atr60 (old ledger entries, thin-history tickers), matching today's behavior.
