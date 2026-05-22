"""Markdown -> HTML renderer with JSON-LD injection and Quant dark-theme styling."""

import json
import re
from html import escape as _esc

from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": True}).enable("table")

CSS_STYLE = """\
<style>
  :root {
    --bg-main: #0d1117;
    --bg-card: #161b22;
    --bg-card-hover: #1c2333;
    --text-primary: #e6edf3;
    --text-muted: #8b949e;
    --accent-green: #00ff9d;
    --accent-red: #ff4d4d;
    --border: #30363d;
    --font-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  }

  *, *::before, *::after { box-sizing: border-box; }

  body {
    background-color: var(--bg-main);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
  }

  /* ---- Typography ---- */

  h1 { font-size: 1.75rem; font-weight: 700; margin: 0 0 0.5rem; letter-spacing: -0.02em; }
  h2 {
    font-size: 1.15rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--text-muted); margin: 2.5rem 0 1rem; padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  a { color: var(--accent-green); text-decoration: none; }
  a:hover { text-decoration: underline; }

  p { margin: 0 0 1rem; }

  /* ---- Tables ---- */

  .table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin: 1.5rem 0;
    border: 1px solid var(--border);
    border-radius: 4px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
    font-size: 0.9rem;
    min-width: 480px;
  }

  th {
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 10px 14px;
    border-bottom: 2px solid var(--border);
    white-space: nowrap;
  }

  td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    font-variant-numeric: tabular-nums;
  }

  tr:last-child td { border-bottom: none; }

  tbody tr:hover { background: var(--bg-card); }

  /* ---- Cards ---- */

  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1.25rem 1.5rem;
    margin: 1.5rem 0;
  }

  .card h2 { margin-top: 0; border-bottom-color: var(--border); }

  .card ul { margin-bottom: 0; }

  /* ---- Win / Loss indicators ---- */

  .win  { color: var(--accent-green); font-weight: 600; }
  .loss { color: var(--accent-red);  font-weight: 600; }

  /* ---- Disclaimer ---- */

  .disclaimer {
    margin-top: 4rem;
    padding: 1.5rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 0.8rem;
    color: var(--text-muted);
    line-height: 1.55;
  }

  .disclaimer h2 {
    font-size: 0.75rem; letter-spacing: 0.1em; margin-top: 0; border-bottom: 1px solid var(--border);
  }

  /* ---- Utility ---- */

  .muted { color: var(--text-muted); }

  hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }

  @media (max-width: 640px) {
    body { padding: 1rem 0.75rem; }
    h1 { font-size: 1.35rem; }
    .card { padding: 1rem; }
  }

  /* ---- Top nav ---- */

  .topnav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.75rem 0; border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem; font-family: var(--font-mono);
    font-size: 0.85rem;
  }
  .topnav a { color: var(--text-muted); margin-left: 1.25rem; }
  .topnav a:hover { color: var(--accent-green); text-decoration: none; }
  .topnav .brand { color: var(--accent-green); font-weight: 700; letter-spacing: 0.04em; }

  /* ---- Hero region ---- */

  .hero { padding: 1.5rem 0 2rem; border-bottom: 1px solid var(--border); }
  .hero .wordmark {
    font-family: var(--font-mono); color: var(--accent-green);
    font-size: 0.75rem; letter-spacing: 0.18em; text-transform: uppercase;
    margin: 0 0 0.5rem;
  }
  .hero h1 { margin: 0 0 0.5rem; font-size: 1.9rem; }
  .hero .tagline { color: var(--text-muted); margin: 0 0 1.5rem; font-size: 0.95rem; }

  .hero-stats {
    display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 0.75rem;
    margin-top: 1rem;
  }
  .stat {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 4px; padding: 0.85rem 1rem;
    font-family: var(--font-mono);
  }
  .stat .num { font-size: 1.5rem; color: var(--text-primary); font-weight: 600; }
  .stat .lbl {
    font-size: 0.7rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.25rem;
  }
  .stat--progress .bar {
    height: 6px; background: var(--bg-main); border-radius: 3px;
    overflow: hidden; margin-top: 0.5rem;
  }
  .stat--progress .bar > span {
    display: block; height: 100%; background: var(--accent-green);
  }
  @media (max-width: 640px) {
    .hero-stats { grid-template-columns: 1fr; }
    .hero h1 { font-size: 1.4rem; }
  }

  /* ---- Sector pills + dots ---- */

  .pill {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 0.72rem; font-family: var(--font-mono);
    background: var(--bg-card); border: 1px solid var(--border);
    color: var(--text-muted); white-space: nowrap;
  }
  .dot {
    display: inline-block; width: 6px; height: 6px; border-radius: 50%;
    margin-right: 6px; vertical-align: middle;
  }
  .dot--mega   { background: #b48cff; }
  .dot--semi   { background: #4d9aff; }
  .dot--broad  { background: #8b949e; }
  .dot--sector { background: #ffa657; }

  /* ---- Table zebra ---- */

  tbody tr:nth-child(even) { background: rgba(255,255,255,0.015); }
  /* hover rule defined once in the Tables section above */
</style>"""

_CARD_SECTIONS = [
    "Today's Setup",
    "Risk Profile",
]


def _wrap_tables(html: str) -> str:
    """Wrap every <table>...</table> in a scrollable container for mobile."""
    return re.sub(
        r"(<table\b[^>]*>.*?</table>)",
        r'<div class="table-wrap">\1</div>',
        html,
        flags=re.DOTALL,
    )


def _wrap_cards(html: str) -> str:
    """Wrap designated h2 sections in card divs."""
    for title in _CARD_SECTIONS:
        html = re.sub(
            rf'(<h2>{re.escape(title)}</h2>.*?)(?=<h2>|</body>)',
            rf'<div class="card">\n\1</div>\n',
            html,
            flags=re.DOTALL,
        )
    return html


def render_html_page(
    *,
    markdown_source: str,
    page_title: str,
    canonical_url: str,
    json_ld_blocks: list[dict],
    description: str | None = None,
    og_image_url: str | None = None,
    theme_color: str | None = None,
    favicon_url: str | None = None,
    apple_touch_icon_url: str | None = None,
) -> str:
    body_html = _md.render(markdown_source)
    body_html = _wrap_tables(body_html)
    body_html = _wrap_cards(body_html)
    head_blocks = "\n".join(
        f'<script type="application/ld+json">{json.dumps(b, separators=(",", ":"))}</script>'
        for b in json_ld_blocks
    )

    meta_lines: list[str] = []
    if description:
        meta_lines.append(
            f'<meta name="description" content="{_esc(description, quote=True)}">'
        )
    if favicon_url:
        meta_lines.append(
            f'<link rel="icon" type="image/svg+xml" href="{_esc(favicon_url, quote=True)}">'
        )
    if apple_touch_icon_url:
        meta_lines.append(
            f'<link rel="apple-touch-icon" href="{_esc(apple_touch_icon_url, quote=True)}">'
        )
    if theme_color:
        meta_lines.append(
            f'<meta name="theme-color" content="{_esc(theme_color, quote=True)}">'
        )
    if og_image_url:
        meta_lines.extend([
            f'<meta property="og:type" content="website">',
            f'<meta property="og:title" content="{_esc(page_title, quote=True)}">',
            f'<meta property="og:url" content="{_esc(canonical_url, quote=True)}">',
            f'<meta property="og:image" content="{_esc(og_image_url, quote=True)}">',
            f'<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{_esc(og_image_url, quote=True)}">',
        ])
        if description:
            meta_lines.append(
                f'<meta property="og:description" content="{_esc(description, quote=True)}">'
            )
    extra_meta = ("\n".join(meta_lines) + "\n") if meta_lines else ""

    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6718270775160916" crossorigin="anonymous"></script>\n'
        '<script defer src="/_vercel/insights/script.js"></script>\n'
        f'<title>{_esc(page_title)}</title>\n'
        f'<link rel="canonical" href="{_esc(canonical_url, quote=True)}">\n'
        f'{extra_meta}'
        f'{CSS_STYLE}\n'
        f'{head_blocks}\n'
        '</head>\n'
        '<body>\n'
        f'{body_html}\n'
        '</body>\n'
        '</html>\n'
    )
