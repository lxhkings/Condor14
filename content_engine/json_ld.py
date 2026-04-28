"""JSON-LD schema emitters for ticker pages.

Three schemas per spec §5.3 / §7.4:
    - FinancialProduct: educational tool product with additionalProperty[]
      (NOT offers.price -- semantically wrong; the prototype bug)
    - BreadcrumbList: site-wide nav schema
    - Article: per-ticker page article schema, author = QuantOptions Data Lab
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
