from datetime import date
from content_engine.json_ld import website_schema, item_list_schema
from ledger.schema import Setup


def _setup(ticker: str) -> Setup:
    return Setup(
        id=f"{ticker}-test",
        ticker=ticker,
        sector="Mega-Cap Tech",
        start_date=date(2026, 5, 1),
        target_exit_date=date(2026, 5, 15),
        expiry_used=date(2026, 5, 15),
        underlying_at_open=100.0,
        atr14_at_open=2.0,
        sma20_at_open=99.0,
        iv_percentile_at_open=50,
        trend_bias="neutral",
        short_call_strike=105.0,
        long_call_strike=110.0,
        short_put_strike=95.0,
        long_put_strike=90.0,
        net_credit_at_open=2.0,
        wing_width=5.0,
        max_profit=2.0,
        max_loss=3.0,
        break_even_upper=107.0,
        break_even_lower=93.0,
        status="open",
        daily_marks=[],
        settlement=None,
    )


def test_website_schema_shape():
    s = website_schema(
        canonical_url="https://example.com/",
        description="Daily iron condor screener and tracker.",
    )
    assert s["@context"] == "https://schema.org"
    assert s["@type"] == "WebSite"
    assert s["url"] == "https://example.com/"
    assert s["name"]
    assert s["description"].startswith("Daily")


def test_item_list_schema_shape_and_order():
    setups = [_setup("AAPL"), _setup("NVDA"), _setup("META")]
    s = item_list_schema(setups, base_url="https://example.com")
    assert s["@type"] == "ItemList"
    assert s["numberOfItems"] == 3
    items = s["itemListElement"]
    assert items[0]["position"] == 1
    assert items[0]["url"] == "https://example.com/aapl/"
    assert items[2]["url"] == "https://example.com/meta/"


def test_item_list_empty_setups():
    s = item_list_schema([], base_url="https://example.com")
    assert s["numberOfItems"] == 0
    assert s["itemListElement"] == []
