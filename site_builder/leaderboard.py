# stock/site_builder/leaderboard.py
"""Cutover gate (this file) and leaderboard data assembly (added in Task 10).

Per spec §7.1: Mode B (Live Performance Tracker) unlocks only when both:
    - settled_count >= 200
    - days_since_first_settlement >= 30
"""

from datetime import date

from ledger.schema import Ledger


def cutover_satisfied(ledger: Ledger, *, today: date) -> bool:
    settled = [s for s in ledger.setups if s.status in ("won", "lost")]
    if len(settled) < 200:
        return False
    if ledger.first_settlement_date is None:
        return False
    return (today - ledger.first_settlement_date).days >= 30
