# AdSense Content Quality Improvement — Design Spec

**Date:** 2026-06-14
**Status:** Approved
**Goal:** Pass Google AdSense review ("low value content" rejection) with minimal changes.

## Problem

Site rejected by AdSense for "low value content." Root causes:

- 55 static HTML pages, ~50 are ticker pages sharing one template
- Each ticker page has ~200-300 words of unique prose; rest is boilerplate
- Google sees many structurally-identical pages as thin content / doorway pages
- Trust signal pages (About, Privacy) are minimal

## Solution Overview

Three-pronged approach to maximize review pass rate:

1. **Trust pages** — new FAQ + Guide pages; rewrite About + Privacy
2. **Hero ticker enrichment** — 8 flagship tickers get company background prose
3. **Tail ticker bulk-up** — all ticker pages get a data-driven summary paragraph + embedded FAQ component

Plus a homepage "Hot Analysis" section to route reviewers toward enriched pages.

## Page Changes

### New Pages

| Page | Template | Content | Word Count |
|---|---|---|---|
| `/faq/` | `faq.md.j2` (new) | Iron condor/options FAQ, reuses `_faq_component.md.j2` | ~1000 |
| `/guide/` | `guide.md.j2` (new) | 14-day iron condor beginner guide | ~800 |

### Rewritten Pages

| Page | Changes |
|---|---|
| `/about/` | Rewrite `about.md.j2`: team philosophy, swing-trading logic, data sources (Futu API), update cadence, contact info. ~600 words. |
| `/privacy/` | Rewrite `privacy.md.j2`: add AdSense disclosure, third-party cookie statement, data collection practices. Formal compliance tone. |

### Modified Pages

| Page | Changes |
|---|---|
| Homepage (both screener + leaderboard) | Add "Featured Ticker Deep Dives" section (4 cards) above data tables. Link to `/guide/`. |
| 8 hero ticker pages | Append company description paragraph (~150 words) between spintax prelude and Today's Setup table. |
| All 50 ticker pages | Append data-driven "Quick Read" summary paragraph after Setup table. Embed `_faq_component.md.j2` before disclaimer. |

## New Data File

**`data/ticker_profiles.json`** — static, hand-written. One entry per hero ticker:

```json
{
  "NVDA": {
    "company_name": "NVIDIA Corporation",
    "sector": "Semiconductors",
    "description": "NVIDIA designs graphics processing units (GPUs) for gaming, data centers, and AI acceleration. As the dominant supplier of AI training hardware, NVDA's share price is sensitive to data-center CapEx cycles, chip export policy, and foundry capacity at TSMC. The stock exhibits above-average implied volatility, which translates into wider iron condor wings and richer net credits relative to broad-market ETFs."
  }
}
```

Fields:

| Field | Usage | Approx. Words |
|---|---|---|
| `company_name` | Ticker page heading, Hot Analysis card | 2-4 |
| `sector` | Reference only (already in ledger) | 1 |
| `description` | Ticker page company section + Hot Analysis card excerpt | ~150 |

**Hero tickers (8):** NVDA, AAPL, MSFT, TSLA, AMZN, META, GOOGL, SPY

Non-hero tickers need no entry in this file.

## Template Changes

### 1. `ticker_page.md.j2` — three insertions

**Insertion A** — after `{{ prelude_md | safe }}`, before `## Today's Setup`:

```jinja2
{% if profile %}
## About {{ profile.company_name }}

{{ profile.description }}
{% endif %}
```

**Insertion B** — after `## Risk Profile` card:

```jinja2
## Quick Read

{{ ticker }} closed at ${{ "%.2f"|format(setup.underlying_at_open) }} with 14-day ATR of ${{ "%.2f"|format(setup.atr14_at_open) }}. Implied volatility sits at the {{ setup.analytics_at_open.vol_percentile|default("--") }}th percentile.
{% if setup.trend_bias == "bullish" %}
Price remains above the 20-day SMA, reflecting constructive daily-chart structure.
{% elif setup.trend_bias == "bearish" %}
Price has slipped below the 20-day SMA, indicating defensive daily-chart posture.
{% else %}
Price hovers near the 20-day SMA in a neutral daily-chart regime.
{% endif %}
The iron condor's upper breakeven of ${{ "%.2f"|format(setup.break_even_upper) }} sits {{ "%.1f"|format((setup.break_even_upper - setup.underlying_at_open) / setup.underlying_at_open * 100) }}% above spot; the lower breakeven of ${{ "%.2f"|format(setup.break_even_lower) }} is {{ "%.1f"|format((setup.underlying_at_open - setup.break_even_lower) / setup.underlying_at_open * 100) }}% below. Risk is capped at ${{ "%.2f"|format(setup.max_loss) }} per spread.
```

**Insertion C** — after `## Related {{ setup.sector }} Tickers`, before `{% endblock %}`:

```jinja2
{% include 'spintax/_faq_component.md.j2' %}
```

### 2. `index_screener.md.j2` + `index_leaderboard.md.j2` — one insertion

After hero stats, before first data table:

```jinja2
## Featured Ticker Deep Dives

<div class="hot-grid">
{% for card in hot_cards %}
<div class="hot-card">
  <h3><a href="/{{ card.ticker|lower }}/">{{ card.ticker }} · {{ card.company_name }}</a></h3>
  <p>{{ card.blurb }}</p>
</div>
{% endfor %}
</div>

[→ How we build iron condor setups: read the guide](/guide/)
```

`hot_cards` built in `build_site.py` from top 4 hero tickers that have open setups. Blurb = first 1-2 sentences of `description` + optional track record line.

### 3. New Templates

**`spintax/_faq_component.md.j2`** — pure static markdown, ~1000 words. Topics:

- What is an iron condor?
- What does ATR-14 measure?
- How is implied volatility (IV) used in strike selection?
- What does "hold to expiration" mean?
- What are the risks of iron condor strategies?
- How are option prices quoted on this site?
- Where does the data come from?

**`faq.md.j2`** — extends `_base.md.j2`, includes `_faq_component.md.j2`.

**`guide.md.j2`** — extends `_base.md.j2`, ~800 word standalone guide.

### 4. Rewrites

- `about.md.j2` — rewrite in-place
- `privacy.md.j2` — rewrite in-place

## Build Pipeline Changes

**`build_site.py`** — minor additions, zero structural refactor:

1. Load `data/ticker_profiles.json` at startup
2. Pass `profile` to ticker page template when ticker has an entry
3. Build `hot_cards` list for homepage templates
4. Handle missing `analytics_at_open` gracefully in Quick Read template (use `|default("--")` filter)
5. Register new pages (`/faq/`, `/guide/`) for rendering + sitemap

**No changes to:** `daily_run.py`, `math_engine/`, `data_source/`, `ledger/`, `content_engine/` spintax logic.

## Visual Design Notes

Hot Analysis grid: 2×2 card layout on desktop, single column on mobile. Cards use existing `--bg-card` + `--border` CSS variables. Green accent links.

FAQ component on ticker pages: wrapped in `<div class="card">` with `## Frequently Asked Questions` heading.

## Review Strategy

- All 8 hero ticker pages + 4 new/rewritten pages form the "reviewer path"
- Homepage Hot Analysis section routes reviewers to these pages first
- Tail ticker pages still benefit from Quick Read + FAQ component, preventing complete nakedness
- Privacy page explicitly names AdSense for policy compliance

## Verification

After build, manual checks:

- [ ] `/faq/` renders, word count >= 800
- [ ] `/guide/` renders, word count >= 600
- [ ] `/about/` renders, mentions AdSense, word count >= 500
- [ ] `/privacy/` renders, mentions AdSense + third-party cookies
- [ ] `/nvda/` shows company description section, Quick Read, FAQ component
- [ ] `/` shows Hot Analysis section with 4 cards
- [ ] Non-hero ticker page (e.g., `/bac/`) shows Quick Read + FAQ, no company description
- [ ] `sitemap.xml` includes `/faq/` and `/guide/`
- [ ] Compliance check passes (no "hypothetical" language violations)
