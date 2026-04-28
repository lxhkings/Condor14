from datetime import date

from ledger.schema import Ledger, SkippedEntry
from ledger.store import LedgerStore


def test_load_returns_empty_ledger_when_file_missing(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    ledger = store.load()
    assert ledger.setups == []
    assert ledger.skipped == []


def test_save_then_load(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    ledger = Ledger(
        setups=[],
        skipped=[SkippedEntry(ticker="PLTR", date=date(2026, 4, 28), reason="x")],
        site_launch_date=date(2026, 4, 28),
    )
    store.save(ledger)
    out = store.load()
    assert out.skipped[0].ticker == "PLTR"
    assert out.site_launch_date == date(2026, 4, 28)


def test_save_is_atomic(tmp_path, monkeypatch):
    """If rename fails midway, the original file must remain intact."""
    path = tmp_path / "ledger.json"
    store = LedgerStore(path)
    # Seed with a valid ledger
    seed = Ledger(
        skipped=[SkippedEntry(ticker="A", date=date(2026, 1, 1), reason="seed")]
    )
    store.save(seed)

    # Now attempt a save where os.replace fails
    import os

    real_replace = os.replace

    def boom(*args, **kwargs):
        raise OSError("simulated failure")

    monkeypatch.setattr("os.replace", boom)

    new = Ledger(
        skipped=[SkippedEntry(ticker="B", date=date(2026, 1, 2), reason="new")]
    )
    try:
        store.save(new)
    except OSError:
        pass
    monkeypatch.setattr("os.replace", real_replace)

    # Original file is intact
    out = store.load()
    assert out.skipped[0].ticker == "A"
