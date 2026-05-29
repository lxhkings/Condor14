# Top Realized P&L Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evergreen top-10 per-ticker board (Ticker | Realized P&L | Trades | Win Rate) to the top of the Mode A homepage so the page always has content even on days with no fresh data.

**Architecture:** New all-time (un-windowed) per-ticker aggregation in `ledger/stats.py` reusing the existing `_summarize()`; a ranking assembler `top_realized_pnl()` in `site_builder/screener.py` wired into `build_screener_data()`; a new table section in `index_screener.md.j2`. Mode B / `per_ticker_stats` / leaderboard are untouched.

**Tech Stack:** Python 3, pytest, Jinja2, markdown-it-py. Run via `uv run pytest`.

---

## File Structure

- Modify `ledger/stats.py` — add `per_ticker_alltime_stats(ledger)` (no time window). Reuses `_summarize()`.
- Modify `site_builder/screener.py` — add `RealizedRow` dataclass + `top_realized_pnl()`; add `"top_realized"` key to `build_screener_data()` return.
- Modify `content_engine/templates/index_screener.md.j2` — add `## Top Realized P&L by Ticker` section above `## Today's Highest Premium Setups`.
- Modify `build_site.py` — pass `top_realized=screener["top_realized"]` into the screener template render call (`_render_index`, lines 178-184).
- Modify tests: `tests/test_ledger_stats.py`, `tests/test_screener.py`, `tests/test_build_site.py`.

---

### Task 1: All-time per-ticker stats

**Files:**
- Modify: `ledger/stats.py` (append new function after `per_ticker_stats`, ~line 72)
- Test: `tests/test_ledger_stats.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ledger_stats.py`:

```python
def test_per_ticker_alltime_includes_old_settlements():
    from ledger.stats import per_ticker_alltime_stats
    ledger = Ledger(setups=[
        _settled("NVDA", date(2026, 1, 1), 100.0, "won"),      # >30 days old
        _settled("NVDA", date(2026, 5, 1), 100.0, "won"),
        _settled("TSLA", date(2026, 4, 25), -300.0, "lost", side="upper"),
    ])
    s = per_ticker_alltime_stats(ledger)
    assert s["NVDA"]["sample_size"] == 2
    assert s["NVDA"]["cumulative_pnl"] == pytest.approx(200.0)
    assert s["NVDA"]["win_rate"] == pytest.approx(1.0)
    assert s["TSLA"]["sample_size"] == 1
    assert s["TSLA"]["cumulative_pnl"] == pytest.approx(-300.0)


def test_per_ticker_alltime_excludes_open_setups():
    from ledger.stats import per_ticker_alltime_stats
    ledger = Ledger(setups=[
        _settled("NVDA", date(2026, 5, 1), 100.0, "won"),
    ])
    ledger.setups.append(Setup(
        id="OPEN", ticker="NVDA", sector="X",
        start_date=date(2026, 5, 1), target_exit_date=date(2026, 5, 15),
        expiry_used=date(2026, 5, 15),
        underlying_at_open=100.0, atr14_at_open=1.0, sma20_at_open=100.0,
        iv_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=105.0, long_call_strike=110.0,
        short_put_strike=95.0,  long_put_strike=90.0,
        net_credit_at_open=1.0, wing_width=5.0,
        max_profit=1.0, max_loss=4.0,
        break_even_upper=106.0, break_even_lower=94.0,
        status="open", daily_marks=[], settlement=None,
    ))
    s = per_ticker_alltime_stats(ledger)
    assert s["NVDA"]["sample_size"] == 1


def test_per_ticker_alltime_empty_ledger():
    from ledger.stats import per_ticker_alltime_stats
    assert per_ticker_alltime_stats(Ledger()) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ledger_stats.py::test_per_ticker_alltime_includes_old_settlements -v`
Expected: FAIL with `ImportError: cannot import name 'per_ticker_alltime_stats'`

- [ ] **Step 3: Write minimal implementation**

Append to `ledger/stats.py` (after `per_ticker_stats`, end of file):

```python
def per_ticker_alltime_stats(ledger: Ledger) -> dict[str, dict]:
    """Per-ticker summary over ALL settled setups (no time window).

    Distinct from per_ticker_stats, which restricts to a 30-day window for the
    Mode B leaderboard. This un-windowed view powers the evergreen Mode A
    Top Realized P&L board.
    """
    by_ticker: dict[str, list] = defaultdict(list)
    for s in ledger.setups:
        if s.settlement is None:
            continue
        by_ticker[s.ticker].append(s)
    return {ticker: _summarize(setups) for ticker, setups in by_ticker.items()}
```

`defaultdict` and `_summarize` are already imported/defined in this module.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ledger_stats.py -v`
Expected: PASS (all, including the 3 new tests)

- [ ] **Step 5: Commit**

```bash
git add ledger/stats.py tests/test_ledger_stats.py
git commit -m "feat(stats): add per_ticker_alltime_stats for evergreen board"
```

---

### Task 2: top_realized_pnl assembler + screener wiring

**Files:**
- Modify: `site_builder/screener.py` (add import, `RealizedRow`, `top_realized_pnl`, dict key)
- Test: `tests/test_screener.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_screener.py`. First add a settled-setup helper near the top (after the existing `_setup` helper):

```python
def _settled(ticker, sector, settled_on, pnl, status="won", side=None) -> Setup:
    from ledger.schema import Settlement
    return Setup(
        id=f"{ticker}-{settled_on}", ticker=ticker, sector=sector,
        start_date=date(2026, 1, 1), target_exit_date=settled_on,
        expiry_used=settled_on,
        underlying_at_open=100.0, atr14_at_open=2.0, sma20_at_open=100.0,
        iv_percentile_at_open=50, trend_bias="neutral",
        short_call_strike=105.0, long_call_strike=110.0,
        short_put_strike=95.0,  long_put_strike=90.0,
        net_credit_at_open=1.0, wing_width=5.0,
        max_profit=1.0, max_loss=4.0,
        break_even_upper=106.0, break_even_lower=94.0,
        status=status, daily_marks=[],
        settlement=Settlement(
            settled_on=settled_on, final_underlying=100.0,
            breached_side=side, final_pnl_per_spread=pnl,
        ),
    )
```

Then add tests:

```python
def test_top_realized_sorted_by_pnl_desc():
    from site_builder.screener import top_realized_pnl
    ledger = Ledger(setups=[
        _settled("A", "S1", date(2026, 5, 1), 50.0),
        _settled("B", "S1", date(2026, 5, 1), 300.0),
        _settled("C", "S1", date(2026, 5, 1), 100.0),
    ])
    rows = top_realized_pnl(ledger)
    assert [r.ticker for r in rows] == ["B", "C", "A"]
    assert rows[0].realized_pnl == 300.0
    assert rows[0].trades == 1
    assert rows[0].win_rate == 1.0


def test_top_realized_aggregates_per_ticker():
    from site_builder.screener import top_realized_pnl
    ledger = Ledger(setups=[
        _settled("NVDA", "S1", date(2026, 5, 1), 100.0, "won"),
        _settled("NVDA", "S1", date(2026, 5, 2), -40.0, "lost", side="upper"),
    ])
    rows = top_realized_pnl(ledger)
    assert len(rows) == 1
    assert rows[0].ticker == "NVDA"
    assert rows[0].realized_pnl == 60.0
    assert rows[0].trades == 2
    assert rows[0].win_rate == 0.5


def test_top_realized_caps_at_10():
    from site_builder.screener import top_realized_pnl
    ledger = Ledger(setups=[
        _settled(f"T{i}", "S1", date(2026, 5, 1), float(i + 1))
        for i in range(15)
    ])
    rows = top_realized_pnl(ledger)
    assert len(rows) == 10
    # highest pnl first: T14 (15.0) ... down to T5 (6.0)
    assert rows[0].ticker == "T14"


def test_top_realized_empty_ledger():
    from site_builder.screener import top_realized_pnl
    assert top_realized_pnl(Ledger()) == []


def test_build_screener_data_includes_top_realized():
    ledger = Ledger(setups=[
        _settled("NVDA", "S1", date(2026, 5, 1), 100.0),
    ])
    data = build_screener_data(ledger, today=date(2026, 5, 10))
    assert "top_realized" in data
    assert data["top_realized"][0].ticker == "NVDA"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_screener.py::test_top_realized_sorted_by_pnl_desc -v`
Expected: FAIL with `ImportError: cannot import name 'top_realized_pnl'`

- [ ] **Step 3: Write minimal implementation**

In `site_builder/screener.py`, add import near the top (after the existing `from ledger.schema import Ledger, Setup`, ~line 14):

```python
from ledger.stats import per_ticker_alltime_stats
```

Add the dataclass and function (after `_newest`, before `build_screener_data`, ~line 45):

```python
@dataclass(frozen=True)
class RealizedRow:
    ticker: str
    realized_pnl: float
    trades: int
    win_rate: float


def top_realized_pnl(ledger: Ledger, top: int = 10) -> list[RealizedRow]:
    stats = per_ticker_alltime_stats(ledger)
    rows = [
        RealizedRow(
            ticker=t,
            realized_pnl=s["cumulative_pnl"],
            trades=s["sample_size"],
            win_rate=s["win_rate"] or 0.0,
        )
        for t, s in stats.items()
        if s["sample_size"] > 0
    ]
    rows.sort(key=lambda r: (-r.realized_pnl, -r.trades, r.ticker))
    return rows[:top]
```

`dataclass` is already imported (line 11). Then add the key to the dict returned by `build_screener_data` (inside the `return {...}`):

```python
        "top_realized": top_realized_pnl(ledger),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_screener.py -v`
Expected: PASS (all, including 5 new tests)

- [ ] **Step 5: Commit**

```bash
git add site_builder/screener.py tests/test_screener.py
git commit -m "feat(screener): add top_realized_pnl board data"
```

---

### Task 3: Template section + build_site wiring

**Files:**
- Modify: `content_engine/templates/index_screener.md.j2` (add section between line 25 paragraph and line 27 heading)
- Modify: `build_site.py:178-184` (`_render_index` screener render call — add `top_realized` kwarg)

- [ ] **Step 1: Add the template section**

In `content_engine/templates/index_screener.md.j2`, insert AFTER the `Live tracking initiated on ...` paragraph (currently line 25) and BEFORE `## Today's Highest Premium Setups`:

```jinja

## Top Realized P&L by Ticker

{% if top_realized %}
| Ticker | Realized P&L | Trades | Win Rate |
| :--- | ---: | ---: | ---: |
{% for r in top_realized %}| [{{ r.ticker }}](/{{ r.ticker|lower }}/) | ${{ "%.2f"|format(r.realized_pnl) }} | {{ r.trades }} | {{ "%.0f"|format(r.win_rate * 100) }}% |
{% endfor %}{% else %}
*No settled setups yet. Live tracking in progress.*
{% endif %}
```

- [ ] **Step 2: Wire the variable into the render call**

In `build_site.py`, the screener branch of `_render_index` (currently lines 178-184) renders `index_screener.md.j2`. Add `top_realized=screener["top_realized"],` to its `.render(...)` kwargs so it reads:

```python
    md = env.get_template("index_screener.md.j2").render(
        site_launch_date=screener["site_launch_date"] or today,
        top_realized=screener["top_realized"],
        highest_premium_setups=screener["highest_premium_setups"],
        sector_heatmap=screener["sector_heatmap"],
        newest_setups=screener["newest_setups"],
        hero=screener["hero"],
    )
```

- [ ] **Step 3: Commit**

```bash
git add content_engine/templates/index_screener.md.j2 build_site.py
git commit -m "feat(site): render Top Realized P&L board on Mode A homepage"
```

---

### Task 4: Homepage integration test

**Files:**
- Test: `tests/test_build_site.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_build_site.py`:

```python
def _seed_ledger_with_settled(path: Path) -> None:
    settled = Setup(
        id="NVDA-2026-04-20", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 6), target_exit_date=date(2026, 4, 20),
        expiry_used=date(2026, 4, 20),
        underlying_at_open=210.0, atr14_at_open=4.0, sma20_at_open=200.0,
        iv_percentile_at_open=55, trend_bias="neutral",
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0,  long_put_strike=195.0,
        net_credit_at_open=1.40, wing_width=5.0,
        max_profit=1.40, max_loss=3.60,
        break_even_upper=231.40, break_even_lower=198.60,
        status="won", daily_marks=[],
        settlement=Settlement(
            settled_on=date(2026, 4, 20), final_underlying=215.0,
            breached_side=None, final_pnl_per_spread=140.0,
        ),
    )
    ledger = Ledger(setups=[settled], site_launch_date=date(2026, 4, 1))
    LedgerStore(path).save(ledger)


def test_homepage_renders_top_realized_board(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    _seed_ledger_with_settled(ledger_path)
    public = tmp_path / "public"
    indexnow_key = tmp_path / "indexnow_key.txt"
    indexnow_key.write_text("k" * 32)

    build(
        ledger_path=ledger_path, public_dir=public,
        host="example.com", today=date(2026, 4, 28),
        indexnow_key_path=indexnow_key,
        last_indexed_path=tmp_path / "last_indexed.json",
        skip_indexnow_ping=True,
    )
    home = (public / "index.html").read_text()
    assert "Top Realized P&L by Ticker" in home
    assert 'href="/nvda/"' in home
    # Mode A still (well under 200 settled)
    assert "Daily Iron Condor Volatility Screener" in home
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_build_site.py::test_homepage_renders_top_realized_board -v`
Expected: FAIL — before Task 3 wiring this fails on the `"Top Realized P&L by Ticker"` assertion. (If Task 3 already complete it should pass; run anyway to confirm.)

- [ ] **Step 3: Run full suite**

Run: `uv run pytest -q`
Expected: PASS (entire suite)

- [ ] **Step 4: Commit**

```bash
git add tests/test_build_site.py
git commit -m "test(site): verify Top Realized P&L board renders on homepage"
```

---

### Task 5: Manual build verification

**Files:** none (verification only)

- [ ] **Step 1: Build the site against real ledger**

Run: `SITE_HOST=condor14.com uv run python build_site.py`
Expected: `build complete: 18 ticker pages`, exit 0 (no compliance violation).

- [ ] **Step 2: Confirm board present in output**

Run: `grep -c "Top Realized P&L by Ticker" public/index.html`
Expected: `1`

Run: `grep -o 'Realized P&L</th>\|Realized P&L |' public/index.html | head -1` (sanity; table rendered)
Expected: a match (table header present).

- [ ] **Step 3: Confirm no banned compliance terms introduced**

Run: `grep -i "hypothetical\|guaranteed\|trading signal" public/index.html || echo "clean"`
Expected: `clean`

---

## Self-Review Notes

- **Spec coverage:** Data layer (Task 1), assembly (Task 2), template + wiring (Task 3), tests (Tasks 1-4), compliance check (Task 5 step 3 + existing build-time scan). Evergreen requirement met via un-windowed `per_ticker_alltime_stats`. Mode B untouched (no task modifies leaderboard/`per_ticker_stats`).
- **Type consistency:** `RealizedRow(ticker, realized_pnl, trades, win_rate)` defined in Task 2, consumed identically in template (Task 3) and tests. `per_ticker_alltime_stats` signature (ledger only, no `today`) consistent across Tasks 1-2.
- **No placeholders:** all steps contain concrete code/commands.
