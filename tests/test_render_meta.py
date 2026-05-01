from site_builder.render import render_html_page


def _render(**overrides):
    base = dict(
        markdown_source="# hi", page_title="T",
        canonical_url="https://example.com/", json_ld_blocks=[],
    )
    base.update(overrides)
    return render_html_page(**base)


def test_default_render_unchanged_no_social_meta():
    html = _render()
    assert '<meta name="description"' not in html
    assert '<meta property="og:' not in html
    assert '<link rel="icon"' not in html


def test_description_meta_emitted():
    html = _render(description="Daily iron condor screener.")
    assert '<meta name="description" content="Daily iron condor screener.">' in html


def test_og_and_twitter_emitted_when_image_set():
    html = _render(
        description="d", og_image_url="https://example.com/og.png",
        page_title="Home",
    )
    assert '<meta property="og:title" content="Home">' in html
    assert '<meta property="og:description" content="d">' in html
    assert '<meta property="og:image" content="https://example.com/og.png">' in html
    assert '<meta property="og:type" content="website">' in html
    assert '<meta property="og:url" content="https://example.com/">' in html
    assert '<meta name="twitter:card" content="summary_large_image">' in html
    assert '<meta name="twitter:image" content="https://example.com/og.png">' in html


def test_favicon_and_theme_color_emitted():
    html = _render(
        favicon_url="/favicon.svg",
        apple_touch_icon_url="/apple-touch-icon.png",
        theme_color="#0d1117",
    )
    assert '<link rel="icon" type="image/svg+xml" href="/favicon.svg">' in html
    assert '<link rel="apple-touch-icon" href="/apple-touch-icon.png">' in html
    assert '<meta name="theme-color" content="#0d1117">' in html


def test_html_escaping_for_meta_content():
    html = _render(description='quotes "are" escaped & <ok>')
    # we should escape so meta content doesn't break attribute quoting
    assert '"are"' not in html
    assert "&quot;are&quot;" in html or "&#34;are&#34;" in html
