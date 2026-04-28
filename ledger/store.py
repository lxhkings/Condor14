"""Atomic read/write of ``ledger.json``."""

from __future__ import annotations

import os
from pathlib import Path

from ledger.schema import Ledger, ledger_from_json, ledger_to_json


class LedgerStore:
    """Persists a :class:`Ledger` to a JSON file with atomic writes."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Ledger:
        """Return the deserialized :class:`Ledger`, or an empty one if the file
        does not exist (first run)."""
        if not self.path.exists():
            return Ledger()
        return ledger_from_json(self.path.read_text())

    def save(self, ledger: Ledger) -> None:
        """Atomically persist *ledger*.

        Write to a temporary sibling file, fsync the temp, then rename over the
        target.  If the process crashes between the write and the rename the
        original file remains intact.
        """
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(ledger_to_json(ledger))
        # Best-effort fsync of the temp file before rename
        with open(tmp, "rb") as f:
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
