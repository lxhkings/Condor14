# stock/site_builder/screener.py
"""Mode A homepage data assembly (pre-cutover screener).

Four panels per spec §7.1:
    - highest_premium_setups: open setups, top 10 by net_credit / max_loss desc
    - sector_heatmap: per-sector aggregation of avg IV percentile and open count
    - newest_setups: setups whose start_date == today
    - top_realized: settled setups ranked by realized P&L
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from ledger.schema import Ledger, Setup
from ledger.stats import per_ticker_alltime_stats


def _ratio(s: Setup) -> float:
    return s.net_credit_at_open / s.max_loss if s.max_loss > 0 else 0.0


def _highest_premium(ledger: Ledger, today: date, top: int = 10) -> list[Setup]:
    today_setups = [s for s in ledger.setups if s.status == "open" and s.start_date == today]
    return sorted(today_setups, key=_ratio, reverse=True)[:top]


def _sector_heatmap(ledger: Ledger) -> list[dict]:
    grouped: dict[str, list[Setup]] = defaultdict(list)
    for s in ledger.setups:
        if s.status == "open":
            grouped[s.sector].append(s)
    rows = []
    for sector, setups in grouped.items():
        avg_iv = sum(s.iv_percentile_at_open for s in setups) // max(len(setups), 1)
        rows.append({
            "sector": sector,
            "avg_iv_percentile": avg_iv,
            "count_open": len(setups),
        })
    rows.sort(key=lambda r: (-r["count_open"], r["sector"]))
    return rows


def _newest(ledger: Ledger, today: date) -> list[Setup]:
    return [s for s in ledger.setups if s.start_date == today]


@dataclass(frozen=True)
class RealizedRow:
    ticker: str
    realized_pnl: float
    trades: int
    win_rate: float


def top_realized_pnl(ledger: Ledger, top: int = 10) -> list[RealizedRow]:
    stats = per_ticker_alltime_stats(ledger)
    rows = [
        RealizedRow(
            ticker=t,
            realized_pnl=s["cumulative_pnl"],
            trades=s["sample_size"],
            win_rate=s["win_rate"] or 0.0,
        )
        for t, s in stats.items()
        if s["sample_size"] > 0
    ]
    rows.sort(key=lambda r: (-r.realized_pnl, -r.trades, r.ticker))
    return rows[:top]


def build_screener_data(ledger: Ledger, *, today: date) -> dict:
    from site_builder.hero import compute_hero_metrics  # local import avoids circular
    if ledger.site_launch_date is None:
        days_since = 0
    else:
        days_since = max(0, (today - ledger.site_launch_date).days)
    return {
        "highest_premium_setups": _highest_premium(ledger, today),
        "sector_heatmap": _sector_heatmap(ledger),
        "newest_setups": _newest(ledger, today),
        "site_launch_date": ledger.site_launch_date,
        "days_since_launch": days_since,
        "hero": compute_hero_metrics(ledger, today=today),
        "top_realized": top_realized_pnl(ledger),
    }
