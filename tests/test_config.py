from config import SECTORS, TICKERS


def test_tickers_has_30_unique_entries():
    assert len(TICKERS) == 30
    assert len(set(TICKERS)) == 30


def test_every_ticker_has_a_sector():
    missing = [t for t in TICKERS if t not in SECTORS]
    assert missing == [], f"tickers without sector: {missing}"


def test_no_orphan_sectors():
    extra = [t for t in SECTORS if t not in TICKERS]
    assert extra == [], f"sectors map has tickers not in TICKERS: {extra}"


def test_each_sector_has_at_least_2_tickers_for_silo_links():
    from collections import Counter
    counts = Counter(SECTORS.values())
    too_small = {s: n for s, n in counts.items() if n < 2}
    assert not too_small, f"sectors with <2 tickers (silo rule): {too_small}"
