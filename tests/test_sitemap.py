# tests/test_sitemap.py
import re
from datetime import date

from site_builder.sitemap import generate_sitemap_xml, generate_robots_txt


def test_sitemap_has_xml_header_and_urlset():
    xml = generate_sitemap_xml(
        base_url="https://example.com",
        ticker_pages=[("nvda", date(2026, 4, 28))],
        static_pages=[("/", date(2026, 4, 28)), ("/methodology/", date(2026, 4, 28))],
    )
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml


def test_sitemap_has_one_url_per_input():
    xml = generate_sitemap_xml(
        base_url="https://example.com",
        ticker_pages=[("nvda", date(2026, 4, 28)), ("tsla", date(2026, 4, 28))],
        static_pages=[("/", date(2026, 4, 28)), ("/methodology/", date(2026, 4, 28))],
    )
    assert len(re.findall(r"<url>", xml)) == 4


def test_sitemap_lastmod_is_iso_8601():
    xml = generate_sitemap_xml(
        base_url="https://example.com",
        ticker_pages=[("nvda", date(2026, 4, 28))],
        static_pages=[],
    )
    assert "<lastmod>2026-04-28</lastmod>" in xml


def test_sitemap_ticker_loc_uses_lowercased_path():
    xml = generate_sitemap_xml(
        base_url="https://example.com",
        ticker_pages=[("nvda", date(2026, 4, 28))],
        static_pages=[],
    )
    assert "<loc>https://example.com/nvda/</loc>" in xml


def test_sitemap_changefreq_for_tickers_is_daily():
    xml = generate_sitemap_xml(
        base_url="https://example.com",
        ticker_pages=[("nvda", date(2026, 4, 28))],
        static_pages=[("/", date(2026, 4, 28))],
    )
    # Tickers daily; static pages weekly
    assert xml.count("<changefreq>daily</changefreq>") == 1
    assert xml.count("<changefreq>weekly</changefreq>") == 1


def test_empty_sitemap_still_valid():
    xml = generate_sitemap_xml(base_url="https://example.com",
                                ticker_pages=[], static_pages=[])
    assert "<urlset" in xml and "</urlset>" in xml


def test_robots_txt_lists_sitemap_url_with_substituted_host():
    txt = generate_robots_txt(host="example.com")
    assert "User-agent: *" in txt
    assert "Allow: /" in txt
    assert "Sitemap: https://example.com/sitemap.xml" in txt


def test_ads_txt_contains_direct_publisher_record():
    from site_builder.sitemap import generate_ads_txt

    txt = generate_ads_txt(publisher_id="pub-6718270775160916")
    assert txt == "google.com, pub-6718270775160916, DIRECT, f08c47fec0942fa0\n"


def test_ads_txt_includes_sovrn_entries_when_passed():
    from site_builder.sitemap import SOVRN_ADS_TXT_ENTRIES, generate_ads_txt

    txt = generate_ads_txt(
        publisher_id="pub-6718270775160916",
        extra_entries=SOVRN_ADS_TXT_ENTRIES,
    )
    # Google line still first
    assert txt.startswith("google.com, pub-6718270775160916, DIRECT, f08c47fec0942fa0\n")
    # Sovrn comment line present
    assert "# SOVRN" in txt
    # Key Sovrn entries
    assert "lijit.com, 606193, DIRECT, fafdf38b16bf6b2b #SOVRN" in txt
    assert "openx.com, 538959099, RESELLER, 6a698e2ec38604c6" in txt
    assert "pubmatic.com, 137711, RESELLER, 5d62403b186f2ace" in txt
    assert "rubiconproject.com, 17960, RESELLER, 0bfd66d529a55807" in txt
    assert "appnexus.com, 1019, RESELLER, f5ab79cb980f11d1" in txt
    # 18 total lines (1 Google + 1 comment + 16 Sovrn entries)
    assert len(txt.strip().split("\n")) == 18


def test_ads_txt_no_extra_entries_still_works():
    from site_builder.sitemap import generate_ads_txt

    txt = generate_ads_txt(publisher_id="pub-6718270775160916")
    assert txt == "google.com, pub-6718270775160916, DIRECT, f08c47fec0942fa0\n"
