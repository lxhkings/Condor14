"""sitemap.xml + robots.txt generators."""

from datetime import date


def generate_sitemap_xml(
    *,
    base_url: str,
    ticker_pages: list[tuple[str, date]],
    static_pages: list[tuple[str, date]],
) -> str:
    base = base_url.rstrip("/")
    urls: list[str] = []
    for ticker, lastmod in ticker_pages:
        urls.append(
            f"  <url>\n"
            f"    <loc>{base}/{ticker.lower()}/</loc>\n"
            f"    <lastmod>{lastmod.isoformat()}</lastmod>\n"
            f"    <changefreq>daily</changefreq>\n"
            f"    <priority>0.8</priority>\n"
            f"  </url>"
        )
    for path, lastmod in static_pages:
        normalized = path if path.startswith("/") else "/" + path
        urls.append(
            f"  <url>\n"
            f"    <loc>{base}{normalized}</loc>\n"
            f"    <lastmod>{lastmod.isoformat()}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.5</priority>\n"
            f"  </url>"
        )
    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def generate_robots_txt(*, host: str) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: https://{host}/sitemap.xml\n"
    )
