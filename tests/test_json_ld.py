# tests/test_json_ld.py
import json
from datetime import date

import pytest

from content_engine.json_ld import (
    article_schema,
    breadcrumb_list,
    financial_product_jsonld,
)
from ledger.schema import Setup


def _setup() -> Setup:
    return Setup(
        id="NVDA-2026-04-28", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 4, 28), target_exit_date=date(2026, 5, 12),
        expiry_used=date(2026, 5, 16),
        underlying_at_open=216.61, atr14_at_open=4.85, sma20_at_open=190.84,
        vol_percentile_at_open=62, trend_bias="bullish",
        short_call_strike=230.0, long_call_strike=235.0,
        short_put_strike=200.0,  long_put_strike=195.0,
        net_credit_at_open=1.42, wing_width=5.0,
        max_profit=1.42, max_loss=3.58,
        break_even_upper=231.42, break_even_lower=198.58,
        status="open", daily_marks=[], settlement=None,
    )


def test_financial_product_has_additional_property_not_offers():
    blob = financial_product_jsonld(_setup())
    assert blob["@type"] == "FinancialProduct"
    assert blob["category"] == "Options Strategy Educational Tool"
    assert "offers" not in blob, "spec §5.3 forbids offers.price; use additionalProperty"
    names = [p["name"] for p in blob["additionalProperty"]]
    assert names == [
        "Net Credit", "Max Profit", "Max Loss",
        "Upper Break-even", "Lower Break-even",
    ]
    for prop in blob["additionalProperty"]:
        assert prop["@type"] == "PropertyValue"
        assert prop["unitText"] == "USD"
        assert isinstance(prop["value"], (int, float))


def test_financial_product_serializes_to_valid_json():
    blob = financial_product_jsonld(_setup())
    s = json.dumps(blob)
    assert json.loads(s) == blob


def test_breadcrumb_list_has_three_positions():
    bc = breadcrumb_list(
        home_url="https://example.com/",
        sector_name="Semiconductors",
        ticker="NVDA",
    )
    assert bc["@type"] == "BreadcrumbList"
    items = bc["itemListElement"]
    assert len(items) == 3
    assert [i["position"] for i in items] == [1, 2, 3]
    assert items[0]["name"] == "Home"
    assert items[1]["name"] == "Semiconductors"
    assert items[2]["name"] == "NVDA"


def test_article_schema_has_published_and_modified():
    art = article_schema(
        ticker="NVDA",
        date_published=date(2026, 4, 28),
        modified=date(2026, 5, 1),
    )
    assert art["@type"] == "Article"
    assert art["author"]["name"] == "QuantOptions Data Lab"
    assert art["datePublished"] == "2026-04-28"
    assert art["dateModified"] == "2026-05-01"


def test_article_schema_modified_defaults_to_published():
    art = article_schema(ticker="NVDA", date_published=date(2026, 4, 28), modified=None)
    assert art["dateModified"] == art["datePublished"]
