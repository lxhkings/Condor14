# Top Realized P&L Board (Mode A Homepage) — Design

**Date:** 2026-05-29
**Status:** Approved for implementation

## Problem

Mode A homepage (`index_screener.md.j2`) panels all key off `start_date == today`
(`screener.py` `_highest_premium` line 22, `_newest` line 44; sector heatmap renders
empty when no open setups). On any day without fresh data (weekends, holidays, or when
the local `daily_run.py` pipeline did not push), every panel collapses to "No setups
today" — the homepage has no browsable content.

## Goal

Add an **evergreen** top-10 board to the Mode A homepage, ranking tickers by cumulative
realized P&L over all settled setups. Because settled setups accumulate permanently and
the board is not time-windowed, the homepage always has core content regardless of daily
update cadence.

## Decisions (from brainstorming)

- **Pool / metric:** settled setups (`status` in won/lost), aggregated **per ticker**,
  ranked by realized P&L (sum of `settlement.final_pnl_per_spread`).
- **Columns (English labels):** `Ticker | Realized P&L | Trades | Win Rate`.
- **Row click target:** existing ticker page `/{ticker}/`. No new pages.
- **Placement:** Mode A, top of page, above "Today's Highest Premium Setups" — the main
  hero content. Mode B (leaderboard) untouched.
- **No "View more":** top 10 only.
- **Evergreen requirement:** aggregate ALL settled setups, NOT the 30-day window used by
  the existing `per_ticker_stats` (which feeds Mode B and must keep its window).

## Architecture (Approach A)

Clean layering — math/aggregation stays in `ledger/stats.py`, assembly in
`site_builder/screener.py`, presentation in the template. Mode B logic is not touched.

### 1. Data layer — `ledger/stats.py`

New function reusing the existing window-agnostic `_summarize()`:

```python
def per_ticker_alltime_stats(ledger: Ledger) -> dict[str, dict]:
    # Same grouping as per_ticker_stats but WITHOUT the 30-day window filter.
    # Group settled setups by ticker, then _summarize() each group.
```

`_summarize()` already returns `sample_size`, `win_rate`, `cumulative_pnl`, etc., and is
independent of any window — it summarizes whatever list it receives. Reuse as-is.

### 2. Assembly layer — `site_builder/screener.py`

```python
@dataclass(frozen=True)
class RealizedRow:
    ticker: str
    realized_pnl: float    # cumulative_pnl
    trades: int            # sample_size
    win_rate: float        # 0..1

def top_realized_pnl(ledger: Ledger, top: int = 10) -> list[RealizedRow]:
    stats = per_ticker_alltime_stats(ledger)
    rows = [
        RealizedRow(t, s["cumulative_pnl"], s["sample_size"], s["win_rate"])
        for t, s in stats.items() if s["sample_size"] > 0
    ]
    rows.sort(key=lambda r: (-r.realized_pnl, -r.trades, r.ticker))
    return rows[:top]
```

Wire a new key `top_realized` into the dict returned by `build_screener_data()`.

### 3. Template — `content_engine/templates/index_screener.md.j2`

New section placed after the hero block and before `## Today's Highest Premium Setups`:

```jinja
## Top Realized P&L by Ticker

{% if top_realized %}
| Ticker | Realized P&L | Trades | Win Rate |
| :--- | ---: | ---: | ---: |
{% for r in top_realized %}| [{{ r.ticker }}](/{{ r.ticker|lower }}/) | ${{ "%.2f"|format(r.realized_pnl) }} | {{ r.trades }} | {{ "%.0f"|format(r.win_rate*100) }}% |
{% endfor %}{% else %}
*No settled setups yet. Live tracking in progress.*
{% endif %}
```

## Data Flow

```
ledger.json
  -> LedgerStore.load()
  -> build_screener_data(ledger, today)
       -> top_realized_pnl(ledger)
            -> per_ticker_alltime_stats(ledger)
                 -> _summarize(per-ticker settled list)
  -> screener["top_realized"]
  -> index_screener.md.j2 render
  -> public/index.html
```

## Error / Edge Handling

- **Zero settled setups:** template `{% else %}` fallback message. (Currently 61 settled,
  so not triggered in practice; handled for new-deploy safety.)
- **win_rate None:** `_summarize` returns non-None `win_rate` whenever settled > 0; the
  `sample_size > 0` guard in `top_realized_pnl` ensures only populated rows reach the row
  construction.
- **Negative P&L:** displayed normally; after descending sort the top 10 are typically
  positive.

## Compliance

- Heading `Top Realized P&L by Ticker` — neutral, no banned language (`guaranteed`,
  `trading signal`, `must close`, imperatives).
- Word "hypothetical" does not appear.
- Section inherits the `_base.md.j2` disclaimer chain.
- Build-time `check_hypothetical_allowlist` scans `public/*.html` as a backstop;
  `build_site.py` exits 2 on violation.

## Testing

- `tests/test_stats.py`: `per_ticker_alltime_stats` aggregates correctly; setups settled
  more than 30 days ago are still counted (the behavior that distinguishes it from the
  windowed `per_ticker_stats`).
- `tests/test_screener.py`: `top_realized_pnl` ordering (realized P&L desc, tiebreak by
  trades desc then ticker), `top=10` truncation, empty ledger returns `[]`.
- `tests/test_build_site.py`: rendered HTML contains `Top Realized P&L` and ticker links.

All tests run offline (no broker connection), consistent with existing suite.

## Out of Scope (YAGNI)

- No new pages, no `/standings/`, no "View more".
- Do not modify Mode B / `per_ticker_stats` / leaderboard.
- No interactive sorting — static table only.
