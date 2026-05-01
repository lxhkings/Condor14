from datetime import date
from pathlib import Path

from build_site import build
from ledger.schema import Ledger
from ledger.store import LedgerStore
from site_builder.compliance import check_hypothetical_allowlist


def test_homepage_copy_passes_compliance(tmp_path: Path):
    ledger_path = tmp_path / "ledger.json"
    LedgerStore(ledger_path).save(Ledger())
    public = tmp_path / "public"
    key = tmp_path / "k.txt"; key.write_text("a" * 32)
    last = tmp_path / "l.json"
    rc = build(
        ledger_path=ledger_path, public_dir=public, host="example.com",
        today=date(2026, 5, 1),
        indexnow_key_path=key, last_indexed_path=last,
        skip_indexnow_ping=True,
    )
    assert rc == 0
    violations = check_hypothetical_allowlist(public)
    assert violations == []
