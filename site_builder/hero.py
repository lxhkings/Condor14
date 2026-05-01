"""Shared hero-region metrics for both Mode A (screener) and Mode B (leaderboard)."""

from datetime import date

from ledger.schema import Ledger

LEADERBOARD_THRESHOLD = 200


def compute_hero_metrics(ledger: Ledger, *, today: date) -> dict:
    settled_count = sum(1 for s in ledger.setups if s.status in ("won", "lost"))
    days_running = (
        max(0, (today - ledger.site_launch_date).days)
        if ledger.site_launch_date is not None
        else 0
    )
    progress_pct = min(100, settled_count * 100 // LEADERBOARD_THRESHOLD)
    return {
        "days_running": days_running,
        "setups_tracked": len(ledger.setups),
        "settled_count": settled_count,
        "progress_pct": progress_pct,
        "progress_label": f"{settled_count} / {LEADERBOARD_THRESHOLD}",
        "cutover_reached": settled_count >= LEADERBOARD_THRESHOLD,
    }
