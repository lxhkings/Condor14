# P1 Content Differentiation — per-ticker Track Record Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-ticker "Track Record" section (real all-time settled stats) to each ticker page and remove duplicate methodology boilerplate, to reverse Google thin-content classification.

**Architecture:** `ledger.stats.per_ticker_alltime_stats` (already exists) is computed once in `build()`, passed per-ticker into `_render_ticker`, and rendered by a conditional block in `ticker_page.md.j2`. No new statistics code.

**Tech Stack:** Python, Jinja2 markdown templates, markdown-it-py → HTML, pytest.

**Spec:** `docs/superpowers/specs/2026-05-30-p1-content-differentiation-design.md`

---

### Task 1: per-ticker Track Record section

**Files:**
- Modify: `build_site.py` (import; compute stats in `build()`; thread `track_record` through `_render_ticker`)
- Modify: `content_engine/templates/ticker_page.md.j2` (insert Track Record block)
- Test: `tests/test_ticker_track_record.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_ticker_track_record.py`:

```python
# tests/test_ticker_track_record.py
from datetime import date
from pathlib import Path

from build_site import build
from ledger.schema import Ledger, Settlement, Setup
from ledger.store import LedgerStore


def _nvda_setup(*, id, start, settled_on=None, status="open", pnl=0.0):
    return Setup(
        id=id, ticker="NVDA", sector="Semiconductors",
        start_date=start, target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61, atr14_at_open=4.85, sma20_at_open=190.84,
        iv_percentile_at_open=62, trend_bias="bullish",
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0, long_put_strike=195.0,
        net_credit_at_open=1.42, wing_width=5.0,
        max_profit=1.42, max_loss=3.58,
        break_even_upper=231.42, break_even_lower=198.58,
        status=status, daily_marks=[],
        settlement=(
            Settlement(
                settled_on=settled_on, final_underlying=215.0,
                breached_side=None, final_pnl_per_spread=pnl,
            ) if settled_on else None
        ),
    )


def _seed_settled(path: Path) -> None:
    setups = [
        _nvda_setup(id="NVDA-A", start=date(2026, 4, 26),
                    settled_on=date(2026, 5, 10), status="won", pnl=1.42),
        _nvda_setup(id="NVDA-B", start=date(2026, 4, 28),
                    settled_on=date(2026, 5, 12), status="lost", pnl=-3.58),
    ]
    LedgerStore(path).save(
        Ledger(setups=setups, site_launch_date=date(2026, 4, 28))
    )


def _build(tmp_path, ledger_path) -> str:
    public = tmp_path / "public"
    key = tmp_path / "indexnow_key.txt"
    key.write_text("k" * 32)
    rc = build(
        ledger_path=ledger_path, public_dir=public, host="example.com",
        today=date(2026, 5, 13), indexnow_key_path=key,
        last_indexed_path=tmp_path / "last_indexed.json",
        skip_indexnow_ping=True,
    )
    assert rc == 0
    return (public / "nvda" / "index.html").read_text()


def test_track_record_renders_with_settled_setups(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _seed_settled(ledger_path)
    html = _build(tmp_path, ledger_path)
    assert "Track Record" in html
    assert "Across 2 settled" in html
    assert "50% of the time" in html
    # cumulative 1.42 - 3.58 = -2.16
    assert "$-2.16" in html
    # worst single loss
    assert "$-3.58" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ticker_track_record.py::test_track_record_renders_with_settled_setups -v`
Expected: FAIL — `"Track Record" in html` is False (section not yet rendered).

- [ ] **Step 3: Add import + compute stats in `build_site.py`**

After the existing line `from ledger.store import LedgerStore` (build_site.py:40), add:

```python
from ledger.stats import per_ticker_alltime_stats
```

In `build()`, immediately after `ledger = LedgerStore(ledger_path).load()` (build_site.py:247), add:

```python
    alltime_stats = per_ticker_alltime_stats(ledger)
```

In the ticker loop, change the `_render_ticker` call (build_site.py:296-299) to pass the stats:

```python
            html = _render_ticker(
                setup=latest[ticker], ledger=ledger, today=today,
                env=env, base_url=base_url,
                track_record=alltime_stats.get(ticker),
            )
```

- [ ] **Step 4: Thread `track_record` through `_render_ticker`**

Change the `_render_ticker` signature (build_site.py:76-83) to add the parameter:

```python
def _render_ticker(
    *,
    setup: Setup,
    ledger: Ledger,
    today: date,
    env: Environment,
    base_url: str,
    track_record: dict | None = None,
) -> str:
```

Add `track_record=track_record,` to the `env.get_template("ticker_page.md.j2").render(...)` call (build_site.py:90-98), e.g. after `peers=peers,`:

```python
    md = env.get_template("ticker_page.md.j2").render(
        ticker=setup.ticker,
        today=today,
        setup=setup,
        prelude_md=prelude_md,
        active_rows=active_rows,
        settled_rows=settled_rows,
        peers=peers,
        track_record=track_record,
    )
```

- [ ] **Step 5: Add Track Record block to template**

In `content_engine/templates/ticker_page.md.j2`, insert the following block immediately AFTER the `## Risk Profile` list (the line `- **Risk-Reward:** 1 : {{ "%.2f"|format(setup.max_loss / setup.max_profit) }}`) and BEFORE `## Methodology Snapshot`:

```jinja
{% if track_record and track_record.sample_size > 0 %}
## Track Record (All-Time Settled)

| Metric | Value |
| :--- | ---: |
| Settled setups | {{ track_record.sample_size }} |
| Win rate | {{ "%.0f"|format(track_record.win_rate * 100) }}% |
| Cumulative P&L | ${{ "%.2f"|format(track_record.cumulative_pnl) }} |
| Worst single loss | ${{ "%.2f"|format(track_record.worst_single_loss) }} |
| Max drawdown | ${{ "%.2f"|format(track_record.max_drawdown) }} |

Across {{ track_record.sample_size }} settled 14-day Iron Condor setups on {{ ticker }}, the structure resolved inside the short strikes {{ "%.0f"|format(track_record.win_rate * 100) }}% of the time, for a cumulative realized result of ${{ "%.2f"|format(track_record.cumulative_pnl) }} per spread.

{% endif %}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_ticker_track_record.py::test_track_record_renders_with_settled_setups -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add build_site.py content_engine/templates/ticker_page.md.j2 tests/test_ticker_track_record.py
git commit -m "feat(seo): add per-ticker Track Record section to ticker pages"
```

---

### Task 2: hide Track Record when no settled history

**Files:**
- Test: `tests/test_ticker_track_record.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ticker_track_record.py`:

```python
def test_track_record_hidden_when_no_settled(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    # Single OPEN setup, never settled -> sample_size 0 for NVDA
    setup = _nvda_setup(id="NVDA-OPEN", start=date(2026, 5, 1))
    LedgerStore(ledger_path).save(
        Ledger(setups=[setup], site_launch_date=date(2026, 4, 28))
    )
    html = _build(tmp_path, ledger_path)
    assert "Track Record" not in html
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_ticker_track_record.py::test_track_record_hidden_when_no_settled -v`
Expected: PASS immediately — the `{% if track_record and track_record.sample_size > 0 %}` guard already hides the section when NVDA has no settled setups (`alltime_stats.get("NVDA")` is None). This test locks that behavior in.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ticker_track_record.py
git commit -m "test(seo): assert Track Record hidden without settled history"
```

---

### Task 3: methodology dedup (remove duplicate boilerplate)

**Files:**
- Modify: `content_engine/templates/ticker_page.md.j2` (`## Methodology Snapshot` block)
- Test: `tests/test_ticker_track_record.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ticker_track_record.py`:

```python
def test_methodology_boilerplate_removed_but_link_kept(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _seed_settled(ledger_path)
    html = _build(tmp_path, ledger_path)
    # Duplicate boilerplate bullets removed
    assert "ATR14-based anchors snapped to listed strikes" not in html
    assert "passive hold-to-expiration" not in html
    # Methodology link still present
    assert "/methodology/" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ticker_track_record.py::test_methodology_boilerplate_removed_but_link_kept -v`
Expected: FAIL — `"ATR14-based anchors snapped to listed strikes" not in html` is False (bullet still present).

- [ ] **Step 3: Remove duplicate bullets, keep link**

In `content_engine/templates/ticker_page.md.j2`, replace the current Methodology Snapshot block:

```jinja
## Methodology Snapshot

- Strike selection: ATR14-based anchors snapped to listed strikes
- Pricing: real-time bid-ask from OPRA via MarketData.app
- Win condition: closing price within short strikes at expiration (passive hold-to-expiration)
- [Full methodology →](/methodology/)
```

with:

```jinja
## Methodology Snapshot

[Full methodology →](/methodology/)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ticker_track_record.py::test_methodology_boilerplate_removed_but_link_kept -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add content_engine/templates/ticker_page.md.j2 tests/test_ticker_track_record.py
git commit -m "feat(seo): dedupe methodology boilerplate on ticker pages, keep link"
```

---

### Task 4: full suite + real build sanity

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -q`
Expected: all pass (189 prior + 3 new = 192).

- [ ] **Step 2: Real build with live ledger**

Run: `SITE_HOST=www.condor14.com uv run python build_site.py`
Expected: exit 0, log `build complete: 18 ticker pages`, no compliance violations (compliance check would return 2 and log if any禁词 introduced).

- [ ] **Step 3: Spot-check rendered output**

Run: `grep -c "Track Record" public/nvda/index.html public/spy/index.html`
Expected: each `1` (NVDA and SPY both have settled history).

Run: `grep -L "Track Record" public/*/index.html` (tickers with no settled history, if any, appear here — acceptable).

- [ ] **Step 4: Commit rebuilt site (only if deploying now)**

```bash
git add public/ data/last_indexed.json
git commit -m "chore(site): rebuild with Track Record sections"
```

---

## Self-Review

**Spec coverage:**
- §4.1 build_site wiring → Task 1 Steps 3-4 ✓
- §4.2 Track Record template block → Task 1 Step 5 ✓
- §4.3 methodology dedup → Task 3 ✓
- §6 tests: 有战绩渲染 (T1), 零战绩隐藏 (T2), 负 P&L (T1 asserts `$-2.16`/`$-3.58`), methodology 去重 (T3) ✓
  - §6 item 4 "叙事句唯一性" — covered implicitly: narrative embeds `win_rate`/`cumulative_pnl` which differ per ticker; T1 asserts the exact NVDA sentence. No separate two-ticker diff test (YAGNI; the template guarantees difference). Acceptable gap.
- §7 边界: zero-settled (T2), win_rate=None guarded by `sample_size>0` (T1/T2), placeholder page untouched (`_render_ticker_placeholder` not modified) ✓

**Placeholder scan:** No TBD/TODO. All steps contain concrete code/commands.

**Type consistency:** `track_record: dict | None` param name matches template var `track_record` and `alltime_stats.get(ticker)` source. Stat keys (`sample_size`, `win_rate`, `cumulative_pnl`, `worst_single_loss`, `max_drawdown`) match `ledger/stats.py::_summarize` return dict.
