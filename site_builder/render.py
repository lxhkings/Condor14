"""Markdown -> HTML renderer with JSON-LD injection and Quant dark-theme styling."""

import json
import re

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
) -> str:
    body_html = _md.render(markdown_source)
    body_html = _wrap_tables(body_html)
    body_html = _wrap_cards(body_html)
    head_blocks = "\n".join(
        f'<script type="application/ld+json">{json.dumps(b, separators=(",", ":"))}</script>'
        for b in json_ld_blocks
    )
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>{page_title}</title>\n'
        f'<link rel="canonical" href="{canonical_url}">\n'
        f'{CSS_STYLE}\n'
        f'{head_blocks}\n'
        '</head>\n'
        '<body>\n'
        f'{body_html}\n'
        '</body>\n'
        '</html>\n'
    )
