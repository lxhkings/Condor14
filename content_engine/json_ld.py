"""JSON-LD schema emitters for ticker and homepage pages.

Ticker-page schemas (spec §5.3 / §7.4):
    - FinancialProduct: educational tool product with additionalProperty[]
    - BreadcrumbList: site-wide nav schema
    - Article: per-ticker page article schema, author = QuantOptions Data Lab

Homepage schemas:
    - WebSite: site-level schema for Google sitelinks
    - ItemList: top-N setups for internal page surfacing
"""

from __future__ import annotations

from datetime import date

from ledger.schema import Setup


def financial_product_jsonld(setup: Setup) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FinancialProduct",
        "name": f"{setup.ticker} 14-Day Iron Condor Educational Tracker",
        "category": "Options Strategy Educational Tool",
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "Net Credit",
             "value": setup.net_credit_at_open, "unitText": "USD"},
            {"@type": "PropertyValue", "name": "Max Profit",
             "value": setup.max_profit, "unitText": "USD"},
            {"@type": "PropertyValue", "name": "Max Loss",
             "value": setup.max_loss, "unitText": "USD"},
            {"@type": "PropertyValue", "name": "Upper Break-even",
             "value": setup.break_even_upper, "unitText": "USD"},
            {"@type": "PropertyValue", "name": "Lower Break-even",
             "value": setup.break_even_lower, "unitText": "USD"},
        ],
    }


def breadcrumb_list(*, home_url: str, sector_name: str, ticker: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": home_url},
            {"@type": "ListItem", "position": 2, "name": sector_name},
            {"@type": "ListItem", "position": 3, "name": ticker},
        ],
    }


def article_schema(
    *, ticker: str, date_published: date, modified: date | None
) -> dict:
    modified = modified or date_published
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{ticker} 14-Day Iron Condor Tracker",
        "author": {"@type": "Organization", "name": "QuantOptions Data Lab"},
        "publisher": {"@type": "Organization", "name": "QuantOptions Data Lab"},
        "datePublished": date_published.isoformat(),
        "dateModified": modified.isoformat(),
    }


def website_schema(*, canonical_url: str, description: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Iron Condor Tracker",
        "url": canonical_url,
        "description": description,
        "publisher": {"@type": "Organization", "name": "QuantOptions Data Lab"},
    }


def item_list_schema(setups: list[Setup], *, base_url: str) -> dict:
    items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "url": f"{base_url}/{s.ticker.lower()}/",
            "name": f"{s.ticker} 14-Day Iron Condor Tracker",
        }
        for i, s in enumerate(setups)
    ]
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "numberOfItems": len(items),
        "itemListElement": items,
    }


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
