# tests/test_render.py
import re

from site_builder.render import render_html_page


def test_doctype_and_html_lang_present():
    html = render_html_page(
        markdown_source="# Hello",
        page_title="Test",
        canonical_url="https://example.com/",
        json_ld_blocks=[],
    )
    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="en">' in html


def test_h1_rendered_from_markdown():
    html = render_html_page(
        markdown_source="# Hello world",
        page_title="t", canonical_url="x", json_ld_blocks=[],
    )
    assert "<h1>Hello world</h1>" in html


def test_title_matches_argument():
    html = render_html_page(
        markdown_source="# x",
        page_title="My Page Title",
        canonical_url="x", json_ld_blocks=[],
    )
    assert "<title>My Page Title</title>" in html


def test_canonical_link_present():
    html = render_html_page(
        markdown_source="# x",
        page_title="t",
        canonical_url="https://example.com/nvda/",
        json_ld_blocks=[],
    )
    assert '<link rel="canonical" href="https://example.com/nvda/">' in html


def test_one_jsonld_block_emits_one_script_tag():
    html = render_html_page(
        markdown_source="# x", page_title="t", canonical_url="x",
        json_ld_blocks=[{"@context": "https://schema.org", "@type": "Article"}],
    )
    matches = re.findall(r'<script type="application/ld\+json">', html)
    assert len(matches) == 1
    assert '"@type":"Article"' in html or '"@type": "Article"' in html


def test_multiple_jsonld_blocks_emit_multiple_script_tags():
    html = render_html_page(
        markdown_source="# x", page_title="t", canonical_url="x",
        json_ld_blocks=[
            {"@type": "FinancialProduct"},
            {"@type": "BreadcrumbList"},
            {"@type": "Article"},
        ],
    )
    matches = re.findall(r'<script type="application/ld\+json">', html)
    assert len(matches) == 3


def test_table_in_markdown_renders():
    md = "| A | B |\n| - | - |\n| 1 | 2 |\n"
    html = render_html_page(
        markdown_source=md, page_title="t", canonical_url="x", json_ld_blocks=[],
    )
    assert '<div class="table-wrap">' in html
    assert "<table>" in html
    assert "<th>A</th>" in html


def test_css_style_is_injected():
    html = render_html_page(
        markdown_source="# x", page_title="t", canonical_url="x", json_ld_blocks=[],
    )
    assert "--bg-main: #0d1117" in html
    assert "--accent-green: #00ff9d" in html
    assert "--font-mono" in html


def test_card_wrapping():
    md = "## Today's Setup\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n## Risk Profile\n\n- **Max Profit:** $1.00\n\n## Other Section\n\nPlain text."
    html = render_html_page(
        markdown_source=md, page_title="t", canonical_url="x", json_ld_blocks=[],
    )
    assert '<div class="card">' in html
    assert html.count('<div class="card">') == 2
    # Card wraps h2 through next h2
    assert '<div class="card">\n<h2>Today\'s Setup</h2>' in html
    assert '<div class="card">\n<h2>Risk Profile</h2>' in html
    # Other Section should NOT be in a card
    assert '<h2>Other Section</h2>' in html
