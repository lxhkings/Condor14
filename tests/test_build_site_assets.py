from datetime import date
from pathlib import Path

from build_site import build
from ledger.schema import Ledger
from ledger.store import LedgerStore


def _seed_empty_ledger(path: Path) -> None:
    LedgerStore(path).save(Ledger())


def test_assets_copied_to_public(tmp_path: Path):
    ledger = tmp_path / "ledger.json"
    _seed_empty_ledger(ledger)
    public = tmp_path / "public"
    indexnow_key = tmp_path / "key.txt"
    indexnow_key.write_text("a" * 32)
    last_indexed = tmp_path / "last.json"

    rc = build(
        ledger_path=ledger, public_dir=public,
        host="example.com", today=date(2026, 5, 1),
        indexnow_key_path=indexnow_key, last_indexed_path=last_indexed,
        skip_indexnow_ping=True,
    )
    assert rc == 0
    assert (public / "favicon.svg").exists()
    assert (public / "favicon.svg").read_text().startswith("<svg")
