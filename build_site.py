# build_site.py
"""Static site build orchestrator.

Step order:
    1. Load ledger.
    2. Decide homepage mode via cutover_satisfied().
    3. Render homepage (screener or leaderboard) -> public/index.html.
    4. Render methodology -> public/methodology/index.html.
    5. For each ticker in TICKERS: render -> public/{ticker_lower}/index.html.
    6. Generate sitemap.xml -> public/sitemap.xml.
    7. Generate robots.txt -> public/robots.txt.
    8. Copy IndexNow key -> public/{key}.txt.
    9. Diff URL list and POST IndexNow ping (best-effort).
   10. Run compliance check (Task 14); exit non-zero on violation.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from config import SECTORS, TICKERS
from content_engine.json_ld import (
    article_schema,
    breadcrumb_list,
    financial_product_jsonld,
)
from content_engine.silo import same_sector_peers
from content_engine.spintax import render_prelude
from content_engine.tracking_log import build_tracking_log
from ledger.schema import Ledger, Setup
from ledger.store import LedgerStore
from site_builder.indexnow import (
    diff_changed_urls,
    ping_indexnow,
    read_key,
)
from site_builder.leaderboard import (
    build_leaderboard_data,
    cutover_satisfied,
)
from site_builder.render import render_html_page
from site_builder.screener import build_screener_data
from site_builder.sitemap import generate_robots_txt, generate_sitemap_xml

log = logging.getLogger("build_site")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

REPO_ROOT = Path(__file__).parent
TEMPLATE_DIR = REPO_ROOT / "content_engine" / "templates"
SOURCE_REPO_URL = "https://github.com/lxhkings/iron-condor-math-engine"


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _render_ticker(
    *,
    setup: Setup,
    ledger: Ledger,
    today: date,
    env: Environment,
    base_url: str,
) -> str:
    prelude_md = render_prelude(
        setup=setup, atr60=setup.atr14_at_open, jinja_env=env,
    )
    tracking = build_tracking_log(ticker=setup.ticker, ledger=ledger, today=today)
    peers = same_sector_peers(setup.ticker)

    md = env.get_template("ticker_page.md.j2").render(
        ticker=setup.ticker,
        today=today,
        setup=setup,
        prelude_md=prelude_md,
        tracking_rows=tracking,
        peers=peers,
        source_repo_url=SOURCE_REPO_URL,
    )
    blocks = [
        financial_product_jsonld(setup),
        breadcrumb_list(
            home_url=f"{base_url}/",
            sector_name=setup.sector,
            ticker=setup.ticker,
        ),
        article_schema(
            ticker=setup.ticker,
            date_published=setup.start_date,
            modified=today,
        ),
    ]
    return render_html_page(
        markdown_source=md,
        page_title=f"{setup.ticker} 14-Day Iron Condor Tracker",
        canonical_url=f"{base_url}/{setup.ticker.lower()}/",
        json_ld_blocks=blocks,
    )


def _render_ticker_placeholder(
    *, ticker: str, today: date, env: Environment, base_url: str,
) -> str:
    """Render a minimal page when a ticker has no current open setup."""
    md = (
        f"# {ticker} 14-Day Iron Condor Tracker -- {today.strftime('%B %d, %Y')}\n\n"
        f"No setup published for {ticker} today. The most common reasons are "
        f"insufficient liquidity on the listed strikes, no expiration in the "
        f"13-16 day target window, or a non-positive net credit. Live tracking "
        f"resumes the next trading day.\n\n"
        f"## Related Tickers\n\n"
    )
    for peer in same_sector_peers(ticker):
        md += f"- [{peer}](/{peer.lower()}/)\n"
    md += "\n---\n\n"
    md += "**DISCLAIMER:** Educational purposes only. Not financial advice.\n"
    return render_html_page(
        markdown_source=md,
        page_title=f"{ticker} 14-Day Iron Condor Tracker",
        canonical_url=f"{base_url}/{ticker.lower()}/",
        json_ld_blocks=[],
    )


def _latest_setup_per_ticker(ledger: Ledger) -> dict[str, Setup]:
    latest: dict[str, Setup] = {}
    for s in ledger.setups:
        if s.ticker not in latest or s.start_date > latest[s.ticker].start_date:
            latest[s.ticker] = s
    return latest


def _render_index(
    *,
    ledger: Ledger,
    today: date,
    env: Environment,
    base_url: str,
) -> tuple[str, str]:
    """Returns (markdown_source, page_title)."""
    if cutover_satisfied(ledger, today=today):
        screener = build_screener_data(ledger, today=today)
        leaderboard = build_leaderboard_data(ledger, today=today)
        md = env.get_template("index_leaderboard.md.j2").render(
            leaderboard_rows=leaderboard,
            highest_premium_setups=screener["highest_premium_setups"],
            sector_heatmap=screener["sector_heatmap"],
        )
        return md, "Live 30-Day Hold-to-Expiration Performance - Iron Condor Tracker"
    else:
        screener = build_screener_data(ledger, today=today)
        md = env.get_template("index_screener.md.j2").render(
            site_launch_date=screener["site_launch_date"] or today,
            highest_premium_setups=screener["highest_premium_setups"],
            sector_heatmap=screener["sector_heatmap"],
            newest_setups=screener["newest_setups"],
        )
        return md, "Daily Iron Condor Volatility Screener"


# Forward-declared; implemented in Task 14.
def check_hypothetical_allowlist(
    public_dir: Path,
) -> list[tuple[Path, int, str]]:
    from site_builder.compliance import (  # noqa: F811
        check_hypothetical_allowlist as _impl,
    )

    return _impl(public_dir)


def build(
    *,
    ledger_path: Path,
    public_dir: Path,
    host: str,
    today: date,
    indexnow_key_path: Path,
    last_indexed_path: Path,
    skip_indexnow_ping: bool = False,
) -> int:
    base_url = f"https://{host}"
    env = _env()
    public_dir.mkdir(parents=True, exist_ok=True)

    ledger = LedgerStore(ledger_path).load()

    # Index page
    index_md, index_title = _render_index(
        ledger=ledger, today=today, env=env, base_url=base_url,
    )
    index_html = render_html_page(
        markdown_source=index_md,
        page_title=index_title,
        canonical_url=f"{base_url}/",
        json_ld_blocks=[],
    )
    _write(public_dir / "index.html", index_html)

    # Methodology page
    methodology_md = env.get_template("methodology.md.j2").render(
        source_repo_url=SOURCE_REPO_URL,
    )
    methodology_html = render_html_page(
        markdown_source=methodology_md,
        page_title="Methodology -- Iron Condor Tracker",
        canonical_url=f"{base_url}/methodology/",
        json_ld_blocks=[],
    )
    _write(public_dir / "methodology" / "index.html", methodology_html)

    # Ticker pages (one per TICKERS member; placeholder if no setup found)
    latest = _latest_setup_per_ticker(ledger)
    ticker_lastmods: list[tuple[str, date]] = []
    for ticker in TICKERS:
        path = public_dir / ticker.lower() / "index.html"
        if ticker in latest:
            html = _render_ticker(
                setup=latest[ticker], ledger=ledger, today=today,
                env=env, base_url=base_url,
            )
            ticker_lastmods.append((ticker.lower(), latest[ticker].start_date))
        else:
            html = _render_ticker_placeholder(
                ticker=ticker, today=today, env=env, base_url=base_url,
            )
            ticker_lastmods.append((ticker.lower(), today))
        _write(path, html)

    # sitemap + robots
    sitemap = generate_sitemap_xml(
        base_url=base_url,
        ticker_pages=ticker_lastmods,
        static_pages=[("/", today), ("/methodology/", today)],
    )
    _write(public_dir / "sitemap.xml", sitemap)
    _write(public_dir / "robots.txt", generate_robots_txt(host=host))

    # IndexNow key file
    key = read_key(indexnow_key_path)
    _write(public_dir / f"{key}.txt", key)

    # IndexNow ping (best-effort)
    if not skip_indexnow_ping:
        all_urls = [f"{base_url}/"] + [f"{base_url}/methodology/"] + [
            f"{base_url}/{t.lower()}/" for t in TICKERS
        ]
        new_urls = diff_changed_urls(
            current_urls=all_urls,
            last_indexed_path=last_indexed_path,
        )
        if new_urls:
            ping_indexnow(key=key, host=host, urls=new_urls)

    # Compliance check (Task 14)
    violations = check_hypothetical_allowlist(public_dir)
    if violations:
        log.error("compliance violations: %d", len(violations))
        for path, line, snippet in violations[:5]:
            log.error("  %s:%d  %s", path, line, snippet)
        return 2

    log.info("build complete: %d ticker pages", len(TICKERS))
    return 0


def main() -> int:
    today = datetime.now(ZoneInfo("America/New_York")).date()
    return build(
        ledger_path=REPO_ROOT / "data" / "ledger.json",
        public_dir=REPO_ROOT / "public",
        host=os.environ.get("SITE_HOST", "iron-condor-tracker.vercel.app"),
        today=today,
        indexnow_key_path=REPO_ROOT / "data" / "indexnow_key.txt",
        last_indexed_path=REPO_ROOT / "data" / "last_indexed.json",
    )


if __name__ == "__main__":
    sys.exit(main())
