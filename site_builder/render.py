"""Markdown -> HTML renderer with JSON-LD injection.

Uses markdown-it-py with table support enabled. Wraps the rendered HTML
in a minimal HTML5 boilerplate. JSON-LD blocks are emitted compactly
(no whitespace) -- Google parses both forms identically and compact saves bytes.
"""

import json

from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": True}).enable("table")


def render_html_page(
    *,
    markdown_source: str,
    page_title: str,
    canonical_url: str,
    json_ld_blocks: list[dict],
) -> str:
    body_html = _md.render(markdown_source)
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
        f'{head_blocks}\n'
        '</head>\n'
        '<body>\n'
        f'{body_html}\n'
        '</body>\n'
        '</html>\n'
    )
