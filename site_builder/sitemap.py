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


SOVRN_ADS_TXT_ENTRIES = [
    "# SOVRN",
    "lijit.com, 606193, DIRECT, fafdf38b16bf6b2b #SOVRN",
    "lijit.com, 606193-eb, DIRECT, fafdf38b16bf6b2b #SOVRN",
    "openx.com, 538959099, RESELLER, 6a698e2ec38604c6",
    "pubmatic.com, 137711, RESELLER, 5d62403b186f2ace",
    "pubmatic.com, 156212, RESELLER, 5d62403b186f2ace",
    "rubiconproject.com, 17960, RESELLER, 0bfd66d529a55807",
    "appnexus.com, 1019, RESELLER, f5ab79cb980f11d1",
    "video.unrulymedia.com, 2444764291, RESELLER",
    "krushmedia.com, AJxF6R572a9M6CaTvK, RESELLER",
    "motorik.io, 100463, RESELLER",
    "smaato.com, 1100056344, RESELLER, 07bcf65f187117b4",
    "smartadserver.com, 4926, RESELLER, 060d053dcf45cbf3",
    "opera.com, pub10014056052800, RESELLER, 55a0c5fd61378de3",
    "axonix.com, 59143, RESELLER, bc385f2b4a87b721",
    "programmaticx.ai, 100464, RESELLER",
    "sharethrough.com, 4926, RESELLER, d53b998a7bd4ecd2",
]


def generate_ads_txt(*, publisher_id: str, extra_entries: list[str] | None = None) -> str:
    lines = [f"google.com, {publisher_id}, DIRECT, f08c47fec0942fa0"]
    if extra_entries:
        lines.extend(extra_entries)
    return "\n".join(lines) + "\n"
