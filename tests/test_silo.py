# tests/test_silo.py
from content_engine.silo import same_sector_peers


def test_nvda_returns_4_alphabetically_sorted_semiconductor_peers():
    peers = same_sector_peers("NVDA")
    assert len(peers) == 4
    assert peers == sorted(peers)
    assert "NVDA" not in peers
    # Semiconductors per config.SECTORS: NVDA, AMD, AVGO, MU, TSM
    expected_pool = {"AMD", "AVGO", "MU", "TSM"}
    assert set(peers) == expected_pool


def test_amd_returns_peers_that_exclude_amd():
    assert "AMD" not in same_sector_peers("AMD")


def test_smaller_sector_returns_what_is_available():
    # "Sector ETF" contains only SMH + ARKK. Asking for n=4 peers of SMH
    # returns only ["ARKK"].
    assert same_sector_peers("SMH") == ["ARKK"]


def test_unknown_ticker_returns_empty():
    assert same_sector_peers("UNKNOWN_TICKER") == []


def test_n_parameter_caps_result_length():
    peers_2 = same_sector_peers("NVDA", n=2)
    assert len(peers_2) == 2
    assert peers_2 == sorted(peers_2)
