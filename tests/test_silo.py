# tests/test_silo.py
from content_engine.silo import same_sector_peers


def test_nvda_returns_4_semiconductor_peers():
    peers = same_sector_peers("NVDA")
    assert len(peers) == 4
    assert peers == sorted(peers)
    assert "NVDA" not in peers
    # Semiconductors per config.SECTORS (sorted, excl NVDA), top 4 by default n=4
    assert peers == ["AMD", "ARM", "AVGO", "INTC"]


def test_amd_returns_peers_that_exclude_amd():
    assert "AMD" not in same_sector_peers("AMD")


def test_sector_etf_has_peers():
    # "Sector ETF" now holds SMH + GLD/SLV/TLT/XLF/XLE/EEM/GDX
    peers = same_sector_peers("SMH")
    assert len(peers) == 4
    assert peers == ["EEM", "GDX", "GLD", "SLV"]


def test_unknown_ticker_returns_empty():
    assert same_sector_peers("UNKNOWN_TICKER") == []


def test_n_parameter_caps_result_length():
    peers_2 = same_sector_peers("NVDA", n=2)
    assert len(peers_2) == 2
    assert peers_2 == sorted(peers_2)
