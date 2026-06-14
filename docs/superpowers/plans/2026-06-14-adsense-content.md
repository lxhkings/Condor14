# AdSense Content Quality Improvement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pass Google AdSense "low value content" review by adding trust pages, enriching hero ticker pages with company descriptions, and bulking up all ticker pages with a Quick Read summary + embedded FAQ component.

**Architecture:** Three-pronged content injection into the existing Jinja2 → `build_site.py` → static HTML pipeline. A new static JSON data file (`data/ticker_profiles.json`) provides company descriptions for 8 hero tickers. Two new standalone pages (`/faq/`, `/guide/`) plus rewritten About/Privacy pages build trust signals. All ticker pages get a data-driven Quick Read paragraph and an embedded FAQ component — zero new API dependencies.

**Tech Stack:** Python 3.x, Jinja2, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-06-14-adsense-content-design.md`

---

### Task 1: Create `data/ticker_profiles.json`

**Files:**
- Create: `data/ticker_profiles.json`

- [ ] **Step 1: Write the data file**

```json
{
  "NVDA": {
    "company_name": "NVIDIA Corporation",
    "sector": "Semiconductors",
    "description": "NVIDIA designs graphics processing units (GPUs) for gaming, data centers, and AI acceleration. As the dominant supplier of AI training hardware, NVDA's share price is sensitive to data-center CapEx cycles, chip export policy, and foundry capacity at TSMC. The stock exhibits above-average implied volatility, which translates into wider iron condor wings and richer net credits relative to broad-market ETFs."
  },
  "AAPL": {
    "company_name": "Apple Inc.",
    "sector": "Technology",
    "description": "Apple designs consumer electronics, software, and services — led by the iPhone ecosystem, Mac, iPad, and growing Services revenue. AAPL is the most widely held US equity and its options market is among the deepest in the world. The stock tends toward moderate realized volatility with periodic bursts around product launch cycles and earnings, making 14-day iron condor structures viable when IV percentile is elevated and the daily chart shows a defined range."
  },
  "MSFT": {
    "company_name": "Microsoft Corporation",
    "sector": "Technology",
    "description": "Microsoft is a diversified enterprise technology company spanning cloud infrastructure (Azure), productivity software (Office 365, LinkedIn), and AI platform services. MSFT's large market capitalization and deep option liquidity produce tight bid-ask spreads, which is favorable for iron condor net credit capture. The stock's realized volatility has historically run below the broad tech sector median, so elevated IV percentile readings on MSFT often signal premium-selling opportunity."
  },
  "TSLA": {
    "company_name": "Tesla Inc.",
    "sector": "Consumer Cyclical",
    "description": "Tesla designs and manufactures electric vehicles, battery storage systems, and solar products. TSLA is known for high implied volatility relative to the broad market, driven by retail sentiment, production delivery numbers, and CEO-driven news flow. The elevated IV environment means iron condor wings are set wider in absolute strike terms and net credits are larger, but tail risk is also materially higher than on lower-volatility tickers — position sizing and strict hold-to-expiration discipline are essential."
  },
  "AMZN": {
    "company_name": "Amazon.com Inc.",
    "sector": "Consumer Cyclical",
    "description": "Amazon operates the world's largest e-commerce marketplace and the leading public cloud platform (AWS). The stock trades with moderate to high implied volatility, influenced by retail spending cycles, Prime Day events, AWS growth rates, and broad tech sentiment. AMZN's deep option liquidity supports competitive bid-ask spreads across a wide strike range, making multi-leg strategies like iron condors executable with acceptable transaction cost assumptions."
  },
  "META": {
    "company_name": "Meta Platforms Inc.",
    "sector": "Communication Services",
    "description": "Meta owns Facebook, Instagram, WhatsApp, and Messenger — the largest social media portfolio globally. Revenue is advertising-driven and sensitive to the macro cycle. META has historically exhibited elevated volatility relative to the S&P 500, with episodic drawdowns tied to regulatory headlines and earnings surprises. The stock's option chain is highly liquid, supporting clean execution of iron condor strikes, and the rich premium environment can produce favorable risk-reward ratios when IV is in the upper tercile of its trailing range."
  },
  "GOOGL": {
    "company_name": "Alphabet Inc.",
    "sector": "Communication Services",
    "description": "Alphabet is the parent of Google, YouTube, and Google Cloud. Search advertising remains the dominant revenue driver, with cloud and subscription services growing. GOOGL tends toward moderate realized volatility and benefits from deep institutional option liquidity. Iron condor setups on GOOGL are most compelling when IV percentile is elevated — typically around earnings cycles or antitrust regulatory events — and the daily chart shows range-bound behavior between well-defined support and resistance levels."
  },
  "SPY": {
    "company_name": "SPDR S&P 500 ETF Trust",
    "sector": "Broad Market",
    "description": "SPY is the most liquid US equity ETF, tracking the S&P 500 index of large-cap US companies. As a diversified basket, SPY exhibits lower realized volatility than individual equities, which means iron condor wings are narrower in percentage terms and net credits are smaller. However, the diversification benefit reduces the probability of large gap moves, and SPY's deep option market ensures tight execution across all strikes. SPY iron condors serve as a benchmark for comparing single-stock condor performance on this site."
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add data/ticker_profiles.json
git commit -m "feat: add ticker profiles for 8 hero tickers

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Create `_faq_component.md.j2`

**Files:**
- Create: `content_engine/templates/spintax/_faq_component.md.j2`

- [ ] **Step 1: Write the FAQ template**

```jinja2
{# content_engine/templates/spintax/_faq_component.md.j2
   Reusable FAQ component — embedded on all ticker pages and on the standalone /faq/ page.
   Pure static markdown, no template variables. ~1000 words. #}

## Frequently Asked Questions

### What is an iron condor?

An iron condor is a four-leg, market-neutral options strategy that combines a bull put spread and a bear call spread on the same underlying, both with the same expiration date. The structure profits when the underlying price closes between the two short strikes at expiration. Maximum profit is limited to the net credit received when opening the position; maximum loss is capped at the wing width minus that credit. The iron condor is a premium-selling strategy — the trader collects option premium upfront and keeps it if the underlying stays within the defined range.

### What does ATR-14 measure?

Average True Range (ATR) is a volatility indicator that measures the average range between a security's daily high and low over a specified period, adjusted for gaps. The "14" refers to the 14-day lookback window. On this site, ATR-14 is computed using Wilder's smoothing method: the initial value is the simple average of the first 14 true ranges, and each subsequent value is `(prior ATR × 13 + current TR) / 14`. ATR anchors every iron condor strike — the short call is placed at roughly 1.5 ATRs above the spot price, and the short put at roughly 1.5 ATRs below, providing a statistical buffer around the expected two-week price range.

### How is implied volatility (IV) used in strike selection?

Implied volatility represents the market's forward-looking expectation of price movement, derived from current option prices. Higher IV translates into wider expected ranges and richer option premiums. On this site, IV percentile — where current IV ranks within its trailing 12-month range — determines how strikes are framed. When IV percentile is high (above 70), premiums are rich relative to recent history, which favors premium-selling strategies. When IV percentile is low (below 30), premiums are compressed and iron condors become less attractive on a risk-reward basis. The system publishes setups regardless of IV percentile to maintain a consistent tracking methodology, but the IV context is included on every ticker page.

### What does "hold to expiration" mean in this data?

Every iron condor setup tracked on this site follows a strictly passive, hold-to-expiration rule. The position is opened at the algorithmically determined strikes and held until the target exit date — normally 14 calendar days after entry. No early exit, no stop-loss, no adjustment is applied. The win condition is simple: if the underlying's closing price on the target exit date falls between the short put strike and the short call strike (inclusive), the setup is recorded as "won." Otherwise it is recorded as "lost." This rule-based approach ensures that every setup is evaluated consistently, making the win-rate and P&L data comparable across tickers and over time.

### What are the risks of iron condor strategies?

Iron condors carry defined but real risk. While maximum loss is capped per spread, the probability of loss is not zero. Risks include: (1) **Gap risk** — the underlying can gap through a short strike overnight, resulting in a loss larger than the initial credit received. (2) **Pin risk** — the underlying may close exactly at a short strike at expiration, creating assignment uncertainty. (3) **Liquidity risk** — wide bid-ask spreads can erode the net credit and increase transaction costs beyond modeled assumptions. (4) **Volatility expansion** — a sudden spike in IV can widen losses on open positions even if the underlying has not breached a short strike. (5) **Early assignment** — American-style options can be exercised before expiration, which is not modeled in this backtest harness. This site's data reflects a passive research methodology; actual live trading involves additional considerations including margin requirements, position sizing, and active risk management.

### How are option prices quoted on this site?

All option prices are sourced from FutuOpenD, Futu's local market data gateway, connected to real-time US options quotes during market hours. Short legs are priced at the bid (the worst realistic fill when selling options to open), and long legs are priced at the ask (the worst realistic fill when buying options for protection). This conservative quoting approach means the net credit shown on each ticker page — `(short call bid + short put bid) - (long call ask + long put ask)` — represents a plausible execution level rather than an idealized mid-price. The actual fill a trader would receive depends on their broker, order routing, and market conditions at the time of execution.

### Where does the data come from?

All underlying price data, option chains, and IV analytics are sourced from FutuOpenD via the futu-api Python SDK. Daily OHLCV bars are cached in a local SQLite database for ATR and SMA computation. The site is updated automatically each US trading day after market close. Historical setups are never retroactively edited — the ledger is append-only and publicly viewable on the site. For full details on formulas, thresholds, and edge cases, see the [methodology page](/methodology/).
```

- [ ] **Step 2: Commit**

```bash
git add content_engine/templates/spintax/_faq_component.md.j2
git commit -m "feat: add reusable FAQ component template

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Create `/faq/` and `/guide/` page templates

**Files:**
- Create: `content_engine/templates/faq.md.j2`
- Create: `content_engine/templates/guide.md.j2`

- [ ] **Step 1: Write `faq.md.j2`**

```jinja2
{# content_engine/templates/faq.md.j2 #}
{% extends "_base.md.j2" %}
{% block body %}
# Iron Condor & Options Trading FAQ

This page answers common questions about iron condor strategies, the indicators used on this site, and how our data is sourced and calculated. The same FAQ section also appears at the bottom of every ticker page for quick reference while reviewing setups.

{% include 'spintax/_faq_component.md.j2' %}
{% endblock %}
```

- [ ] **Step 2: Write `guide.md.j2`**

```jinja2
{# content_engine/templates/guide.md.j2 #}
{% extends "_base.md.j2" %}
{% block body %}
# Beginner's Guide: 14-Day Iron Condor Strategy

This guide explains the core concepts behind the 14-day iron condor setups tracked on this site. It is written for readers who are familiar with basic options terminology but new to multi-leg strategies.

## What Is an Iron Condor?

An iron condor is a four-leg options strategy that combines two vertical spreads — a bull put spread and a bear call spread — on the same underlying, expiring on the same date. The trader sells an out-of-the-money put spread below the current price and an out-of-the-money call spread above it. The goal is for the underlying to stay between the two short strikes through expiration. If it does, both spreads expire worthless and the trader keeps the full net credit.

## Why 14 Days?

Fourteen calendar days is a deliberate sweet spot. Shorter durations (weekly options) amplify gamma risk — small price moves near expiration can swing P&L dramatically. Longer durations (30+ days) expose the position to more macro and earnings events. Two weeks balances these concerns: enough time for theta decay to work, short enough to limit event exposure. The expiration is selected from the nearest available option series in the 13–16 day window, preferring the one closest to 14 days.

## How Strikes Are Selected

Strikes are not picked by discretion. The system follows a fixed, repeatable formula:

1. Compute the 14-day Average True Range (ATR-14) using Wilder's smoothing method.
2. Set the short call anchor at `spot + 1.5 × ATR-14`, snapped to the nearest listed strike.
3. Set the short put anchor at `spot - 1.5 × ATR-14`, snapped to the nearest listed strike.
4. Set wing width to `max(0.5 × ATR-14, one strike increment)`, snapped outward for the long strikes.

The 1.5× ATR multiplier is chosen so that, under normal distribution assumptions, the underlying is expected to stay inside the short strikes roughly 68–80% of the time over a two-week window. This is a statistical anchor, not a prediction.

## Understanding the Profit and Loss Profile

The iron condor's P&L is structured and bounded:

- **Max Profit** = Net Credit received at open. Realized when the underlying closes between the short strikes at expiration.
- **Max Loss** = Wing Width − Net Credit. Realized when the underlying closes beyond either long strike at expiration.
- **Breakeven Points** = Short Call + Net Credit (upper) and Short Put − Net Credit (lower).

Between the breakeven points, the position is profitable or at breakeven. Beyond them, losses accrue dollar-for-dollar up to the max loss cap.

## What "Hold to Expiration" Means

Every setup tracked on this site follows a single, non-discretionary rule: open at the algorithmically determined prices and hold until the target exit date. There is no early close, no adjustment, and no stop-loss. If the underlying closes between the two short strikes on the exit date, the setup is recorded as **won**. Otherwise it is recorded as **lost**. This consistent rule-set means the track record data published here is a clean statistical sample, not a curated set of favorable outcomes.

## Risks to Understand

Iron condors are defined-risk, but that risk is real. Key risks include:

- **Gap moves** — The underlying can open beyond a breakeven point overnight.
- **Volatility expansion** — If implied volatility spikes, the mark-to-market loss can be large even if the underlying is still inside the short strikes.
- **Early assignment** — American-style options can be exercised before expiration, which is not simulated in this backtest harness.
- **Liquidity** — Wide bid-ask spreads or low open interest can make fills worse than the conservative quotes shown here.

No setup on this site should be interpreted as trading advice. The data is published for educational research purposes. See the disclaimer on every page and the full [methodology](/methodology/) for details.

## How to Use This Site

- **Homepage** — See today's highest-premium setups, sector volatility heatmap, and featured ticker deep dives.
- **Ticker Pages** — Each tracked symbol has a dedicated page showing today's setup, all-time track record, active setups, and settlement history.
- **Methodology** — Every formula, filter, and edge case is documented with no omissions.

Start with the ticker pages linked under "Featured Ticker Deep Dives" on the homepage — those include extra company context alongside the data tables.
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add content_engine/templates/faq.md.j2 content_engine/templates/guide.md.j2
git commit -m "feat: add FAQ and Guide page templates

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Rewrite `about.md.j2` and `privacy.md.j2`

**Files:**
- Modify: `content_engine/templates/about.md.j2` (full rewrite)
- Modify: `content_engine/templates/privacy.md.j2` (full rewrite)

- [ ] **Step 1: Rewrite `about.md.j2`**

```jinja2
{# content_engine/templates/about.md.j2 #}
{% extends "_base.md.j2" %}
{% block body %}
# About Condor14

Condor14 is an automated quantitative research project operated by **QuantOptions Data Lab**. It computes, publishes, and tracks 14-day iron condor setups across 30+ liquid US equities and ETFs — every trading day, algorithmically, with no human discretion.

## Our Philosophy

We believe that options strategy research should be transparent, reproducible, and judged by its full track record — not by curated highlights. Every setup on this site is generated by a fixed set of rules documented on the [methodology page](/methodology/). No trade is cherry-picked. No losing setup is hidden. The ledger is append-only and publicly viewable.

## The Strategy Logic

We focus on the 14-day iron condor for a specific reason: it sits at the intersection of statistical edge and mechanical simplicity. The iron condor is a premium-selling, market-neutral structure that profits from time decay and range-bound price action rather than from directional predictions. The 14-day window is long enough for theta decay to compound and short enough to limit event exposure.

Our strike selection is anchored to the 14-day Average True Range (ATR-14), a volatility measure that adapts to each underlying's recent behavior. The short strikes are placed at approximately 1.5 ATRs from the spot price — a distance chosen so that, under normal market conditions, the underlying is expected to remain within the short strike envelope over a two-week horizon.

We track from open to expiration with no early exits, no stop-losses, and no adjustments. This is deliberate: it produces a clean, consistent data set where every setup is evaluated under the same rules. Real traders use stops and adjustments — and should — but a research harness must be internally consistent to produce meaningful statistics.

## Data Sources

All market data — underlying quotes, option chains, implied volatility analytics, and daily OHLCV bars — is sourced from **FutuOpenD**, Futu's local market data gateway, via the futu-api Python SDK. Historical daily bars are cached in a local SQLite database for indicator computation.

Data is refreshed each US trading day after the market close (approximately 4:30 PM Eastern). The site is updated via an automated pipeline that runs Monday through Friday.

## Transparency

- **The methodology page** documents every formula, threshold, and edge case. No black boxes.
- **The public ledger** (`data/ledger.json`) is committed to the site repository and contains every setup and every skip reason since launch.
- **Settlement is rule-based.** A setup wins if the underlying closes between the two short strikes at the target exit date, inclusive. Otherwise it loses. No judgment calls.

## What This Site Is Not

Condor14 is not a trading signal service, an advisory platform, or a broker. It does not recommend any trade, position size, or strategy. The setups shown are research artifacts generated by a mechanical process. Options trading involves substantial risk of loss and is not suitable for all investors. Past performance — including win rates and cumulative P&L shown on this site — does not guarantee future results.

## Contact

Questions, corrections, or feedback: [contact page](/contact/) or email `{{ publisher_email }}`.
{% endblock %}
```

- [ ] **Step 2: Rewrite `privacy.md.j2`**

```jinja2
{# content_engine/templates/privacy.md.j2 #}
{% extends "_base.md.j2" %}
{% block body %}
# Privacy Policy

**Last updated:** June 14, 2026

## Who We Are

Condor14 is operated by QuantOptions Data Lab. Our website address is `https://www.condor14.com`. Contact: `{{ publisher_email }}`.

## Information We Collect

### Automatically Collected Data

When you visit Condor14, certain information is automatically collected by our hosting infrastructure (Vercel) and analytics services:

- **Vercel Analytics** — anonymized page view data including referrer URL, page path, country-level geographic location, and device type. No personally identifiable information (PII) is collected by Vercel Analytics. See [Vercel's Privacy Policy](https://vercel.com/legal/privacy-policy).
- **Server Logs** — standard web server log data (IP address, timestamp, requested URL, user-agent string, HTTP status code) is collected by Vercel's edge network for operational purposes. These logs are retained for a limited period and are not used for marketing or user profiling by Condor14.

### Data We Do NOT Collect

- We do not operate user accounts, comment systems, or email newsletter signups.
- We do not use web forms that collect personal data (except if you choose to email us directly).
- We do not sell, rent, or share any visitor data with third parties for marketing purposes.

## Cookies

### Essential Cookies

Condor14 itself does not set any first-party cookies. No login, session, or preference cookies are used.

### Third-Party Cookies

**Google AdSense:** This site displays advertisements served by Google AdSense. Google and its partners use cookies to serve ads based on your prior visits to this site and other websites on the internet. These cookies allow Google and its partners to show you ads that may be more relevant to your interests.

- Google's use of advertising cookies enables it and its partners to serve ads based on your visit to this site and/or other sites on the internet.
- You may opt out of personalized advertising by visiting [Google's Ads Settings](https://www.google.com/settings/ads) or the broader industry opt-out page at [www.aboutads.info](https://www.aboutads.info/).
- Third-party vendors, including Google, use cookies to serve ads based on a user's prior visits to this website.

**Google AdSense participates in the IAB Europe Transparency & Consent Framework and complies with its Specifications and Policies.** For users in the European Economic Area (EEA) and the United Kingdom, Google will show a consent management message as required by applicable regulations.

## Embedded Content from Other Websites

This site does not embed content (videos, images, articles, etc.) from other websites. All content is generated and hosted on Condor14.

## How Long We Retain Data

- Vercel Analytics data is retained according to Vercel's data retention policies (typically 12 months for aggregated analytics).
- Server logs are retained by Vercel for operational purposes, typically for a period of days to weeks.

## Your Rights

Depending on your jurisdiction, you may have rights regarding your personal data, including the right to access, correct, delete, or port your data. Since Condor14 does not collect or store personal data directly, exercising these rights is generally limited to the data held by our third-party service providers (Vercel, Google). Please contact us at `{{ publisher_email }}` with any privacy-related inquiries.

## Changes to This Policy

We may update this privacy policy from time to time. Changes will be posted on this page with an updated "Last updated" date. We encourage you to review this policy periodically.

## Contact

For questions about this privacy policy, contact: `{{ publisher_email }}`.
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add content_engine/templates/about.md.j2 content_engine/templates/privacy.md.j2
git commit -m "feat: rewrite About and Privacy pages for AdSense compliance

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Modify `ticker_page.md.j2` — three insertions

**Files:**
- Modify: `content_engine/templates/ticker_page.md.j2`

- [ ] **Step 1: Add company profile section after prelude, before Today's Setup**

Replace the block from `{{ prelude_md | safe }}` through `## Today's Setup` with:

```jinja2
{{ prelude_md | safe }}

{% if profile %}
## About {{ profile.company_name }}

{{ profile.description }}
{% endif %}

## Today's Setup
```

Exact edit: insert after line 6 (`{{ prelude_md | safe }}`), before line 8 (`## Today's Setup`). (Line numbers reference current file as read.)

```jinja2
{% if profile %}
## About {{ profile.company_name }}

{{ profile.description }}
{% endif %}

```

- [ ] **Step 2: Add Quick Read paragraph after Risk Profile card**

After the Risk Profile card (lines 30-33), insert:

```jinja2
## Quick Read

{{ ticker }} closed at ${{ "%.2f"|format(setup.underlying_at_open) }} with a 14-day ATR of ${{ "%.2f"|format(setup.atr14_at_open) }}. Implied volatility ranks at the {{ setup.vol_percentile_at_open }}th percentile of its trailing 12-month range. {% if setup.trend_bias == "bullish" %}Price remains above the 20-day SMA of ${{ "%.2f"|format(setup.sma20_at_open) }}, reflecting constructive daily-chart structure.{% elif setup.trend_bias == "bearish" %}Price has slipped below the 20-day SMA of ${{ "%.2f"|format(setup.sma20_at_open) }}, indicating defensive daily-chart posture.{% else %}Price hovers near the 20-day SMA of ${{ "%.2f"|format(setup.sma20_at_open) }} in a neutral daily-chart regime.{% endif %} The iron condor's upper breakeven of ${{ "%.2f"|format(setup.break_even_upper) }} sits {{ "%.1f"|format((setup.break_even_upper - setup.underlying_at_open) / setup.underlying_at_open * 100) }}% above spot; the lower breakeven of ${{ "%.2f"|format(setup.break_even_lower) }} is {{ "%.1f"|format((setup.underlying_at_open - setup.break_even_lower) / setup.underlying_at_open * 100) }}% below. Risk is capped at ${{ "%.2f"|format(setup.max_loss) }} per spread.
```

- [ ] **Step 3: Add FAQ component before endblock**

After the `## Related {{ setup.sector }} Tickers` block (line 87), and before `{% endblock %}` (line 88), insert:

```jinja2
{% include 'spintax/_faq_component.md.j2' %}
```

- [ ] **Step 4: Commit**

```bash
git add content_engine/templates/ticker_page.md.j2
git commit -m "feat: enrich ticker pages with company profile, Quick Read, and FAQ

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Add Hot Analysis section to homepage templates

**Files:**
- Modify: `content_engine/templates/index_screener.md.j2`
- Modify: `content_engine/templates/index_leaderboard.md.j2`

- [ ] **Step 1: Add Hot Analysis to `index_screener.md.j2`**

Insert after line 23 (end of hero section `</div>`, before `Live tracking initiated on...`), add:

```jinja2

## Featured Ticker Deep Dives

{% if hot_cards %}
<div class="hot-grid">
{% for card in hot_cards %}
<div class="hot-card">
  <h3><a href="/{{ card.ticker|lower }}/">{{ card.ticker }} &middot; {{ card.company_name }}</a></h3>
  <p>{{ card.blurb }}</p>
</div>
{% endfor %}
</div>
{% endif %}

[&rarr; How we build iron condor setups: read the guide](/guide/)

```

- [ ] **Step 2: Same insertion for `index_leaderboard.md.j2`**

The hero section structure is identical. Insert the same block after the hero `</div>`, before the leaderboard table section.

- [ ] **Step 3: Commit**

```bash
git add content_engine/templates/index_screener.md.j2 content_engine/templates/index_leaderboard.md.j2
git commit -m "feat: add Hot Analysis section to homepage templates

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Modify `build_site.py` — data loading and template data passing

**Files:**
- Modify: `build_site.py`

This task makes all the `build_site.py` changes needed. Four changes:

1. Load `ticker_profiles.json` at startup (fail-safe: empty dict on any error)
2. Pass `profile` to `_render_ticker` + pass `hot_cards` to index templates
3. Render new `/faq/` and `/guide/` pages
4. Register `/faq/` and `/guide/` in sitemap and IndexNow URL list

- [ ] **Step 1: Add `_load_ticker_profiles()` helper and import `json`**

Add `import json` to the imports block (after `import sys`), and add the helper function before `_env()`:

```python
import json


def _load_ticker_profiles() -> dict:
    """Load ticker company profiles from data/ticker_profiles.json.
    Returns empty dict on any failure — profile enrichment is best-effort."""
    profiles_path = REPO_ROOT / "data" / "ticker_profiles.json"
    try:
        return json.loads(profiles_path.read_text())
    except Exception:
        log.warning("ticker_profiles.json not found or invalid; skipping profiles")
        return {}
```

- [ ] **Step 2: Modify `_render_ticker` to accept and pass `profile`**

Change the function signature from:
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

To:
```python
def _render_ticker(
    *,
    setup: Setup,
    ledger: Ledger,
    today: date,
    env: Environment,
    base_url: str,
    track_record: dict | None = None,
    profile: dict | None = None,
) -> str:
```

Then in the `env.get_template("ticker_page.md.j2").render(...)` call, add `profile=profile,`:

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
        profile=profile,
    )
```

- [ ] **Step 3: Modify `_render_index` to accept `hot_cards`**

Change signature from:
```python
def _render_index(
    *,
    ledger: Ledger,
    today: date,
    env: Environment,
    base_url: str,
) -> tuple[str, str, dict]:
```

To:
```python
def _render_index(
    *,
    ledger: Ledger,
    today: date,
    env: Environment,
    base_url: str,
    hot_cards: list[dict] | None = None,
) -> tuple[str, str, dict]:
```

In the screener branch, add `hot_cards=hot_cards,`:
```python
        md = env.get_template("index_screener.md.j2").render(
            site_launch_date=screener["site_launch_date"] or today,
            top_realized=screener["top_realized"],
            highest_premium_setups=screener["highest_premium_setups"],
            sector_heatmap=screener["sector_heatmap"],
            newest_setups=screener["newest_setups"],
            hero=screener["hero"],
            hot_cards=hot_cards,
        )
```

In the leaderboard branch, add `hot_cards=hot_cards,`:
```python
        md = env.get_template("index_leaderboard.md.j2").render(
            leaderboard_rows=leaderboard,
            highest_premium_setups=screener["highest_premium_setups"],
            sector_heatmap=screener["sector_heatmap"],
            hero=screener["hero"],
            hot_cards=hot_cards,
        )
```

- [ ] **Step 4: Build `hot_cards` and load profiles in `build()`, pass to render functions**

In `build()`, after line 260 (`alltime_stats = ...`), add:

```python
    profiles = _load_ticker_profiles()

    # Build hot_cards for homepage: top 4 hero tickers that have open setups
    hot_cards: list[dict] = []
    _hero_order = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "SPY"]
    for t in _hero_order:
        if len(hot_cards) >= 4:
            break
        p = profiles.get(t)
        if not p:
            continue
        ls = latest.get(t) if 'latest' in dir() else None
        # latest is populated later; build hot_cards after latest is computed
    ```

Wait — `latest` is computed later (line 327 currently). We need to either move the `latest` computation up or build `hot_cards` after it. The cleanest approach: compute `latest` before building `hot_cards`, and build `hot_cards` before `_render_index`.

Move the `latest = _latest_setup_per_ticker(ledger)` line to right after loading profiles, then build `hot_cards`, then pass to `_render_index`:

```python
    ledger = LedgerStore(ledger_path).load()
    alltime_stats = per_ticker_alltime_stats(ledger)
    profiles = _load_ticker_profiles()
    latest = _latest_setup_per_ticker(ledger)

    # Hot cards for homepage: top 4 hero tickers that have profiles
    hot_cards: list[dict] = []
    _hero_order = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "SPY"]
    for t in _hero_order:
        if len(hot_cards) >= 4:
            break
        p = profiles.get(t)
        if not p:
            continue
        blurb = p["description"].split(". ")[0] + "."
        tr = alltime_stats.get(t)
        if tr and tr.get("sample_size", 0) > 0:
            blurb += f" {t}'s {tr['sample_size']} settled iron condor cycles on this site have closed at a {tr['win_rate']*100:.0f}% win rate to date."
        hot_cards.append({
            "ticker": t,
            "company_name": p["company_name"],
            "blurb": blurb,
        })
```

Then pass `hot_cards=hot_cards` to `_render_index`:

```python
    index_md, index_title, screener = _render_index(
        ledger=ledger, today=today, env=env, base_url=base_url,
        hot_cards=hot_cards,
    )
```

And remove the duplicate `latest = _latest_setup_per_ticker(ledger)` line that currently appears later (line 327):

```python
    # Ticker pages (one per TICKERS member; placeholder if no setup found)
    for ticker in TICKERS:
        path = public_dir / ticker.lower() / "index.html"
        if ticker in latest:
            html = _render_ticker(
                setup=latest[ticker], ledger=ledger, today=today,
                env=env, base_url=base_url,
                track_record=alltime_stats.get(ticker),
                profile=profiles.get(ticker),
            )
```

- [ ] **Step 5: Render `/faq/` and `/guide/` pages**

After the trust pages loop (lines 305-322), add:

```python
    # FAQ page
    faq_md = env.get_template("faq.md.j2").render()
    faq_html = render_html_page(
        markdown_source=faq_md,
        page_title="Iron Condor & Options Trading FAQ -- Condor14",
        canonical_url=f"{base_url}/faq/",
        json_ld_blocks=[],
        favicon_url="/favicon.svg",
        apple_touch_icon_url="/apple-touch-icon.png",
        theme_color=THEME_COLOR,
    )
    _write(public_dir / "faq" / "index.html", faq_html)

    # Guide page
    guide_md = env.get_template("guide.md.j2").render()
    guide_html = render_html_page(
        markdown_source=guide_md,
        page_title="Beginner's Guide: 14-Day Iron Condor Strategy -- Condor14",
        canonical_url=f"{base_url}/guide/",
        json_ld_blocks=[],
        favicon_url="/favicon.svg",
        apple_touch_icon_url="/apple-touch-icon.png",
        theme_color=THEME_COLOR,
    )
    _write(public_dir / "guide" / "index.html", guide_html)
```

- [ ] **Step 6: Register `/faq/` and `/guide/` in sitemap and IndexNow URL list**

Update the sitemap `static_pages` list (line 350-353):

```python
    sitemap = generate_sitemap_xml(
        base_url=base_url,
        ticker_pages=ticker_lastmods,
        static_pages=[
            ("/", today), ("/methodology/", today),
            ("/about/", today), ("/privacy/", today), ("/contact/", today),
            ("/faq/", today), ("/guide/", today),
        ],
    )
```

Update the IndexNow `all_urls` list (lines 366-371):

```python
        all_urls = (
            [
                f"{base_url}/", f"{base_url}/methodology/",
                f"{base_url}/about/", f"{base_url}/privacy/", f"{base_url}/contact/",
                f"{base_url}/faq/", f"{base_url}/guide/",
            ]
            + [f"{base_url}/{t.lower()}/" for t in TICKERS]
        )
```

- [ ] **Step 7: Run build to verify no errors**

```bash
uv run python build_site.py
```
Expected: `INFO build_site build complete: N ticker pages`, exit code 0.

- [ ] **Step 8: Commit**

```bash
git add build_site.py
git commit -m "feat: integrate profiles, FAQ, Guide, Hot Analysis into build pipeline

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Update tests

**Files:**
- Modify: `tests/test_trust_pages.py`

- [ ] **Step 1: Add test for new pages rendering**

```python
def test_faq_and_guide_pages_render(tmp_path):
    public = _build(tmp_path)
    for slug in ("faq", "guide"):
        page = public / slug / "index.html"
        assert page.is_file(), f"{slug} page missing"
        content = page.read_text()
        assert len(content) > 500, f"{slug} page too short: {len(content)} chars"
```

- [ ] **Step 2: Add test for sitemap including new pages**

```python
def test_sitemap_includes_faq_and_guide(tmp_path):
    public = _build(tmp_path)
    sitemap = (public / "sitemap.xml").read_text()
    assert "/faq/" in sitemap
    assert "/guide/" in sitemap
```

- [ ] **Step 3: Add test for ticker page Quick Read and FAQ embed**

```python
def test_ticker_page_has_quick_read_and_faq(tmp_path):
    public = _build(tmp_path)
    html = (public / "nvda" / "index.html").read_text()
    assert "Quick Read" in html
    assert "Frequently Asked Questions" in html
    assert "What is an iron condor?" in html
    assert "upper breakeven" in html.lower()
```

- [ ] **Step 4: Add test for profile section on hero ticker (when profile exists)**

This test needs `ticker_profiles.json`. The `_build` helper sets up a tmp_path; we need to also create the profiles file:

```python
import json


def test_ticker_page_shows_profile_for_hero_ticker(tmp_path):
    # Create profiles file with NVDA entry
    profiles_path = tmp_path / "ticker_profiles.json"
    # Override REPO_ROOT... actually _load_ticker_profiles reads from REPO_ROOT.
    # We need a different approach: test that profile=None works (no crash),
    # and test profile injection separately.
    pass
```

Since `_load_ticker_profiles()` reads from `REPO_ROOT / "data" / "ticker_profiles.json"` and tests use `tmp_path`, the test build will hit the real file if it exists or gracefully return `{}`. The test for profile injection is best done as an integration check by running the real build and verifying the NVDA page contains "About NVIDIA Corporation".

```python
def test_ticker_page_no_crash_without_profiles(tmp_path):
    """Profile injection is best-effort; build must pass without profiles file."""
    public = _build(tmp_path)
    html = (public / "nvda" / "index.html").read_text()
    # Even without profiles, the page should still render
    assert "NVDA" in html
    assert "Today's Setup" in html
```

- [ ] **Step 5: Add test for homepage Hot Analysis section**

```python
def test_homepage_has_hot_analysis_section(tmp_path):
    public = _build(tmp_path)
    html = (public / "index.html").read_text()
    assert "Featured Ticker Deep Dives" in html
    assert "/guide/" in html
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/test_trust_pages.py -v
```
Expected: all tests pass, including new ones.

- [ ] **Step 7: Run full test suite**

```bash
uv run pytest -v
```
Expected: all existing tests still pass (no regressions).

- [ ] **Step 8: Commit**

```bash
git add tests/test_trust_pages.py
git commit -m "test: add tests for FAQ, Guide, Quick Read, Hot Analysis

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Final verification build

- [ ] **Step 1: Run full build and inspect output**

```bash
uv run python build_site.py
```

- [ ] **Step 2: Spot-check rendered pages**

```bash
# Check FAQ page exists and has content
grep -c "Frequently Asked Questions" public/faq/index.html
# Expected: >= 1

# Check Guide page exists and has content
grep -c "Beginner's Guide" public/guide/index.html
# Expected: >= 1

# Check NVDA page has profile section (if ticker_profiles.json committed)
grep -c "About NVIDIA" public/nvda/index.html
# Expected: >= 1

# Check NVDA page has Quick Read
grep -c "Quick Read" public/nvda/index.html
# Expected: >= 1

# Check BAC page (non-hero) has Quick Read but no profile section
grep -c "Quick Read" public/bac/index.html
# Expected: >= 1

# Check sitemap includes new pages
grep -c "/faq/" public/sitemap.xml
# Expected: >= 1

# Check compliance
echo $?  # should be 0
```

- [ ] **Step 3: Check compliance passes**

```bash
uv run python build_site.py; echo "exit=$?"
```
Expected: `exit=0`

- [ ] **Step 4: Final commit if any output changes**

```bash
git add public/
git status
```
Only commit if generated output has changed as expected.
