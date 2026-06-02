# Trust & Authority Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add About / Privacy Policy / Contact pages, a site-wide footer nav, and an `Organization` JSON-LD block, so the site clears Google AdSense review and strengthens YMYL E-E-A-T for search indexing.

**Architecture:** Pure static-generator additions. Three new Jinja2 markdown templates extend the existing `_base.md.j2` chain; one footer-nav partial is included by `_base` (and injected into the placeholder path that bypasses `_base`); `build_site.py` renders the three pages and wires them into sitemap + IndexNow; `json_ld.py` gains an `organization_schema()` emitter surfaced on the homepage.

**Tech Stack:** Python, Jinja2 markdown templates, markdown-it-py → HTML, pytest.

**Spec:** `docs/superpowers/specs/2026-06-02-trust-authority-pages-design.md`

---

## File Structure

- Create: `content_engine/templates/_footer_nav.md.j2` — single source of footer nav links.
- Create: `content_engine/templates/about.md.j2` — About page (entity, E-E-A-T).
- Create: `content_engine/templates/privacy.md.j2` — Privacy Policy (AdSense-mandated cookie/ad disclosure).
- Create: `content_engine/templates/contact.md.j2` — Contact page (publisher email).
- Modify: `content_engine/templates/_base.md.j2` — include footer nav before disclaimer.
- Modify: `content_engine/json_ld.py` — add `organization_schema()`.
- Modify: `site_builder/render.py` — add `.sitenav` CSS rule.
- Modify: `build_site.py` — `PUBLISHER_EMAIL` const; render 3 pages; footer nav in placeholder; homepage Organization block; sitemap + IndexNow URLs.
- Test: `tests/test_trust_pages.py` — new test file.

---

### Task 1: Organization JSON-LD emitter

**Files:**
- Modify: `content_engine/json_ld.py` (append function)
- Test: `tests/test_trust_pages.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_trust_pages.py`:

```python
# tests/test_trust_pages.py
from datetime import date
from pathlib import Path

from content_engine.json_ld import organization_schema


def test_organization_schema_shape():
    org = organization_schema(
        base_url="https://example.com", contact_email="contact@example.com"
    )
    assert org["@type"] == "Organization"
    assert org["name"] == "QuantOptions Data Lab"
    assert org["url"] == "https://example.com/"
    assert org["contactPoint"]["email"] == "contact@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_trust_pages.py::test_organization_schema_shape -v`
Expected: FAIL — `ImportError: cannot import name 'organization_schema'`.

- [ ] **Step 3: Implement `organization_schema`**

Append to `content_engine/json_ld.py` (after `item_list_schema`):

```python
def organization_schema(*, base_url: str, contact_email: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "QuantOptions Data Lab",
        "url": f"{base_url}/",
        "description": (
            "Automated educational research project tracking 14-day iron "
            "condor setups computed from real OPRA options quotes."
        ),
        "contactPoint": {
            "@type": "ContactPoint",
            "email": contact_email,
            "contactType": "customer support",
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_trust_pages.py::test_organization_schema_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add content_engine/json_ld.py tests/test_trust_pages.py
git commit -m "feat(seo): add Organization JSON-LD emitter"
```

---

### Task 2: Footer nav partial + propagation

**Files:**
- Create: `content_engine/templates/_footer_nav.md.j2`
- Modify: `content_engine/templates/_base.md.j2`
- Modify: `build_site.py` (placeholder path; `_render_ticker_placeholder`)
- Modify: `site_builder/render.py` (`.sitenav` CSS)
- Test: `tests/test_trust_pages.py` (append)

This task adds the footer nav to every page. The nav links to `/about/`, `/privacy/`, `/contact/` which do not exist until Task 3 — that is expected; this task only asserts the links are emitted.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trust_pages.py`:

```python
from build_site import build
from ledger.schema import Ledger, Settlement, Setup
from ledger.store import LedgerStore


def _nvda_setup() -> Setup:
    return Setup(
        id="NVDA-A", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 26), target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61, atr14_at_open=4.85, sma20_at_open=190.84,
        vol_percentile_at_open=62, trend_bias="bullish",
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0, long_put_strike=195.0,
        net_credit_at_open=1.42, wing_width=5.0,
        max_profit=1.42, max_loss=3.58,
        break_even_upper=231.42, break_even_lower=198.58,
        status="won", daily_marks=[],
        settlement=Settlement(
            settled_on=date(2026, 5, 10), final_underlying=215.0,
            breached_side=None, final_pnl_per_spread=1.42,
        ),
        atr60_at_open=4.20,
    )


def _build(tmp_path: Path) -> Path:
    """Run a full build; return the public dir. NVDA gets a full ticker page;
    all other TICKERS render placeholder pages."""
    ledger_path = tmp_path / "ledger.json"
    LedgerStore(ledger_path).save(
        Ledger(setups=[_nvda_setup()], site_launch_date=date(2026, 4, 28))
    )
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
    return public


def test_footer_nav_on_all_page_types(tmp_path):
    public = _build(tmp_path)
    home = (public / "index.html").read_text()
    ticker = (public / "nvda" / "index.html").read_text()      # full ticker page
    placeholder = (public / "spy" / "index.html").read_text()  # no setup -> placeholder
    for html in (home, ticker, placeholder):
        assert "/about/" in html
        assert "/privacy/" in html
        assert "/contact/" in html
        assert "/methodology/" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_trust_pages.py::test_footer_nav_on_all_page_types -v`
Expected: FAIL — `/privacy/` not in HTML (footer nav not yet emitted).

- [ ] **Step 3: Create the footer nav partial**

Create `content_engine/templates/_footer_nav.md.j2`:

```jinja
{# content_engine/templates/_footer_nav.md.j2 #}
<nav class="sitenav">

[Home](/) · [Methodology](/methodology/) · [About](/about/) · [Privacy Policy](/privacy/) · [Contact](/contact/)

</nav>
```

- [ ] **Step 4: Include footer nav in `_base.md.j2`**

Replace the entire body of `content_engine/templates/_base.md.j2`:

```jinja
{# stock/content_engine/templates/_base.md.j2 — top-of-page slot for Markdown title.
   The HTML <head>/<body> wrapper is added by site_builder.render. This template
   only emits Markdown content; child templates override the body block.
#}
{% block body %}{% endblock %}
{% include "_footer_nav.md.j2" %}
{% include "_disclaimer.md.j2" %}
```

- [ ] **Step 5: Inject footer nav into the placeholder path**

In `build_site.py`, in `_render_ticker_placeholder`, add the footer-nav render immediately BEFORE the disclaimer render. Change:

```python
    for peer in same_sector_peers(ticker):
        md += f"- [{peer}](/{peer.lower()}/)\n"
    md += env.get_template("_disclaimer.md.j2").render(
    )
```

to:

```python
    for peer in same_sector_peers(ticker):
        md += f"- [{peer}](/{peer.lower()}/)\n"
    md += env.get_template("_footer_nav.md.j2").render()
    md += env.get_template("_disclaimer.md.j2").render(
    )
```

- [ ] **Step 6: Add `.sitenav` CSS**

In `site_builder/render.py`, in the `CSS_STYLE` string, add the `.sitenav` rule immediately after the `.muted` utility rule. Change:

```css
  /* ---- Utility ---- */

  .muted { color: var(--text-muted); }
```

to:

```css
  /* ---- Utility ---- */

  .muted { color: var(--text-muted); }

  .sitenav {
    margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border);
    font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);
  }
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/test_trust_pages.py::test_footer_nav_on_all_page_types -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add content_engine/templates/_footer_nav.md.j2 content_engine/templates/_base.md.j2 build_site.py site_builder/render.py tests/test_trust_pages.py
git commit -m "feat(seo): add site-wide footer nav to all page types"
```

---

### Task 3: About / Privacy / Contact pages + build wiring

**Files:**
- Create: `content_engine/templates/about.md.j2`
- Create: `content_engine/templates/privacy.md.j2`
- Create: `content_engine/templates/contact.md.j2`
- Modify: `build_site.py` (import; `PUBLISHER_EMAIL`; render 3 pages; homepage Organization block; sitemap; IndexNow)
- Test: `tests/test_trust_pages.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trust_pages.py`:

```python
from build_site import PUBLISHER_EMAIL


def test_trust_pages_render(tmp_path):
    public = _build(tmp_path)
    for slug in ("about", "privacy", "contact"):
        page = public / slug / "index.html"
        assert page.is_file()
        assert len(page.read_text()) > 0


def test_privacy_page_has_adsense_requisites(tmp_path):
    public = _build(tmp_path)
    html = (public / "privacy" / "index.html").read_text().lower()
    assert "google" in html
    assert "cookie" in html
    assert "https://www.google.com/settings/ads" in html
    assert "aboutads.info" in html
    assert PUBLISHER_EMAIL.lower() in html


def test_contact_page_has_email(tmp_path):
    public = _build(tmp_path)
    html = (public / "contact" / "index.html").read_text()
    assert PUBLISHER_EMAIL in html
    assert f"mailto:{PUBLISHER_EMAIL}" in html


def test_sitemap_includes_trust_pages(tmp_path):
    public = _build(tmp_path)
    sitemap = (public / "sitemap.xml").read_text()
    assert "/about/" in sitemap
    assert "/privacy/" in sitemap
    assert "/contact/" in sitemap


def test_homepage_has_organization_jsonld(tmp_path):
    public = _build(tmp_path)
    html = (public / "index.html").read_text()
    assert '"@type":"Organization"' in html
    assert PUBLISHER_EMAIL in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_trust_pages.py -v -k "trust_pages_render or adsense or contact_page or sitemap_includes or organization_jsonld"`
Expected: FAIL — `ImportError: cannot import name 'PUBLISHER_EMAIL'` (and pages/sitemap entries missing).

- [ ] **Step 3: Create the About template**

Create `content_engine/templates/about.md.j2`:

```jinja
{# content_engine/templates/about.md.j2 #}
{% extends "_base.md.j2" %}
{% block body %}
# About

Condor14 is an automated, educational research project operated by **QuantOptions Data Lab**. Every trading day it computes a single 14-day iron condor setup for each tracked US equity and ETF, then tracks that setup live to expiration and records the realized outcome in a public ledger.

## What this site is

- An **educational data project**. It demonstrates how a fully rule-based options strategy behaves over time across many underlyings.
- **Algorithmically generated.** No human discretion selects strikes, entries, or exits. Every number is produced by the formulas documented on the [methodology page](/methodology/).
- **Transparent.** Each setup is published when it opens and settled strictly by holding to expiration, so the win rates and cumulative results shown reflect a consistent, passive research harness.

## What this site is not

This site does not constitute financial advice, a solicitation, or a recommendation to buy or sell any security. The setups are research artifacts, not instructions. Options trading involves substantial risk; see the disclaimer at the bottom of every page.

## Data

Options quotes and underlying prices are sourced from OPRA via MarketData.app. Strike anchoring, net-credit pricing, and settlement rules are fully specified on the [methodology page](/methodology/).

## Contact

Questions, data corrections, or feedback: see the [contact page](/contact/).
{% endblock %}
```

- [ ] **Step 4: Create the Privacy template**

Create `content_engine/templates/privacy.md.j2`:

```jinja
{# content_engine/templates/privacy.md.j2 #}
{% extends "_base.md.j2" %}
{% block body %}
# Privacy Policy

QuantOptions Data Lab operates Condor14 as a static, content-only website. This policy explains what data is and is not collected when you visit.

## Information we collect

This site does not require registration and does not ask you for personal information. We do not operate login accounts, comment forms, or newsletters, and we do not sell personal information.

## Cookies and third-party advertising

This site displays ads served by Google AdSense. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this and other websites.

- Google's use of advertising cookies enables it and its partners to serve ads to you based on your visit to this site and/or other sites on the Internet.
- You may opt out of personalized advertising by visiting [Google Ads Settings](https://www.google.com/settings/ads).
- You may opt out of a third-party vendor's use of cookies for personalized advertising by visiting [www.aboutads.info](https://www.aboutads.info/choices/).

For more information on how Google uses data when you use its partners' sites or apps, see [Google's policies](https://policies.google.com/technologies/partner-sites).

## Analytics

Aggregate, non-identifying request logs may be retained by our hosting provider for security and performance. These logs are not used to identify individual visitors.

## Changes to this policy

This policy may be updated as the site evolves. Material changes will be reflected on this page.

## Contact

Questions about this policy: {{ publisher_email }} (see also the [contact page](/contact/)).
{% endblock %}
```

- [ ] **Step 5: Create the Contact template**

Create `content_engine/templates/contact.md.j2`:

```jinja
{# content_engine/templates/contact.md.j2 #}
{% extends "_base.md.j2" %}
{% block body %}
# Contact

Condor14 is operated by **QuantOptions Data Lab**.

For data corrections, methodology questions, or general feedback, email:

[{{ publisher_email }}](mailto:{{ publisher_email }})

We read every message but cannot provide individualized financial advice. For how the published setups are computed, see the [methodology page](/methodology/).
{% endblock %}
```

- [ ] **Step 6: Add import + `PUBLISHER_EMAIL` to `build_site.py`**

In `build_site.py`, add `organization_schema` to the existing `content_engine.json_ld` import block (currently imports `article_schema, breadcrumb_list, financial_product_jsonld, item_list_schema, website_schema`):

```python
from content_engine.json_ld import (
    article_schema,
    breadcrumb_list,
    financial_product_jsonld,
    item_list_schema,
    organization_schema,
    website_schema,
)
```

Add a module constant after `THEME_COLOR = "#0d1117"`:

```python
PUBLISHER_EMAIL = "contact@condor14.com"
```

- [ ] **Step 7: Render the three trust pages in `build()`**

In `build_site.py`, immediately AFTER the methodology page `_write(...)` call (the line `_write(public_dir / "methodology" / "index.html", methodology_html)`), insert:

```python
    # Trust & authority pages (about / privacy / contact)
    for slug, template_name, title in (
        ("about", "about.md.j2", "About -- Iron Condor Tracker"),
        ("privacy", "privacy.md.j2", "Privacy Policy -- Iron Condor Tracker"),
        ("contact", "contact.md.j2", "Contact -- Iron Condor Tracker"),
    ):
        page_md = env.get_template(template_name).render(
            publisher_email=PUBLISHER_EMAIL,
        )
        page_html = render_html_page(
            markdown_source=page_md,
            page_title=title,
            canonical_url=f"{base_url}/{slug}/",
            json_ld_blocks=[],
            favicon_url="/favicon.svg",
            apple_touch_icon_url="/apple-touch-icon.png",
            theme_color=THEME_COLOR,
        )
        _write(public_dir / slug / "index.html", page_html)
```

(The `about.md.j2` template ignores the `publisher_email` kwarg; passing it uniformly keeps the loop DRY.)

- [ ] **Step 8: Add Organization block to homepage**

In `build_site.py`, in `build()`, change the `homepage_blocks` list to insert the Organization block between `website_schema(...)` and `item_list_schema(...)`:

```python
    homepage_blocks = [
        website_schema(
            canonical_url=f"{base_url}/",
            description=HOMEPAGE_DESCRIPTION,
        ),
        organization_schema(base_url=base_url, contact_email=PUBLISHER_EMAIL),
        item_list_schema(
            _unique_by_ticker(screener["highest_premium_setups"]),
            base_url=base_url,
        ),
    ]
```

- [ ] **Step 9: Add trust pages to sitemap**

In `build_site.py`, change the `generate_sitemap_xml` call's `static_pages` argument:

```python
    sitemap = generate_sitemap_xml(
        base_url=base_url,
        ticker_pages=ticker_lastmods,
        static_pages=[
            ("/", today), ("/methodology/", today),
            ("/about/", today), ("/privacy/", today), ("/contact/", today),
        ],
    )
```

- [ ] **Step 10: Add trust pages to IndexNow URL list**

In `build_site.py`, in the IndexNow block, change the `all_urls` assignment:

```python
        all_urls = (
            [
                f"{base_url}/", f"{base_url}/methodology/",
                f"{base_url}/about/", f"{base_url}/privacy/", f"{base_url}/contact/",
            ]
            + [f"{base_url}/{t.lower()}/" for t in TICKERS]
        )
```

- [ ] **Step 11: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_trust_pages.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 12: Commit**

```bash
git add content_engine/templates/about.md.j2 content_engine/templates/privacy.md.j2 content_engine/templates/contact.md.j2 build_site.py tests/test_trust_pages.py
git commit -m "feat(seo): add About/Privacy/Contact pages + Organization schema"
```

---

### Task 4: Full suite + real build sanity

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -q`
Expected: all pass (prior suite + 6 new trust-page tests).

- [ ] **Step 2: Real build with live ledger**

Run: `SITE_HOST=www.condor14.com uv run python build_site.py`
Expected: exit 0, log `build complete: 18 ticker pages`, no compliance violations (a violation would return 2 and log the offending file). This also overwrites any stale `public/*` content.

- [ ] **Step 3: Spot-check rendered trust pages**

Run: `ls public/about/index.html public/privacy/index.html public/contact/index.html`
Expected: all three exist.

Run: `grep -c "aboutads.info" public/privacy/index.html`
Expected: `1`.

Run: `grep -c "/privacy/" public/nvda/index.html public/index.html`
Expected: each `1` (footer nav present).

Run: `grep -c '"@type":"Organization"' public/index.html`
Expected: `1`.

- [ ] **Step 4: Commit rebuilt site**

```bash
git add public/ data/last_indexed.json
git commit -m "chore(site): rebuild with trust & authority pages"
```

---

## Post-Implementation ACTION (out of code scope)

- **Before submitting AdSense review:** ensure `contact@condor14.com` is a reachable inbox (domain catch-all or forwarding). If it cannot be configured, change `PUBLISHER_EMAIL` in `build_site.py` to a real reachable address and rebuild.
- **In GSC:** run URL Inspection → Request Indexing for `/about/`, `/privacy/`, `/contact/`.
- **In AdSense console:** resubmit the site for review once the pages are live.

---

## Self-Review

**Spec coverage:**
- §3.1 about/privacy/contact/_footer_nav templates → Task 2 Step 3 (footer), Task 3 Steps 3-5 ✓
- §3.2 `_base.md.j2` footer include → Task 2 Step 4 ✓
- §3.3 build_site wiring (PUBLISHER_EMAIL, render 3 pages, placeholder footer, homepage org, sitemap, indexnow) → Task 2 Step 5 (placeholder), Task 3 Steps 6-10 ✓
- §3.4 `organization_schema` → Task 1 ✓
- §3.5 `.sitenav` CSS → Task 2 Step 6 ✓
- §6 tests: 三页渲染 (T3 test_trust_pages_render), 隐私要件 (T3 test_privacy_page_has_adsense_requisites), 联系页 (T3 test_contact_page_has_email), 页脚导航传播 (T2 test_footer_nav_on_all_page_types), sitemap (T3 test_sitemap_includes_trust_pages), Organization (T3 test_homepage_has_organization_jsonld), 合规 build==0 (every `_build` asserts rc==0), json_ld 单测 (T1) ✓
- §7 合规：新文案无禁词；about 用既有 disclaimer 措辞 ("does not constitute financial advice, a solicitation, or a recommendation")；build rc==0 在每个 build 测试中验证 ✓
- §8 ACTION/风险 → Post-Implementation ACTION 段 ✓

**Placeholder scan:** No TBD/TODO. All code/commands concrete.

**Type consistency:** `organization_schema(*, base_url, contact_email)` signature identical across Task 1 def, Task 3 homepage call, and T1 test. `PUBLISHER_EMAIL` defined Task 3 Step 6, used Steps 7-10 + imported in tests. Template var `publisher_email` matches the render kwarg in Task 3 Step 7 and the `{{ publisher_email }}` usage in privacy/contact templates. `Setup(...)` fixture in Task 2 uses exact current schema fields (`vol_percentile_at_open`, optional `atr60_at_open`) per `ledger/schema.py`.
