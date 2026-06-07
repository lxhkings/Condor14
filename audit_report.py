"""离线报告：比对发布定价 vs 保守定价的偏差与盈利。只读 ledger，不写。

用法:
    uv run python audit_report.py [data/ledger.json]
"""

from __future__ import annotations

import sys
from statistics import median

from ledger.schema import Ledger, Setup
from ledger.store import LedgerStore


def _conservative_pnl(s: Setup) -> float | None:
    """已结算 setup 在保守 credit 下的每价差 P&L；输赢与定价无关。"""
    qa = s.quote_audit
    if qa is None or s.settlement is None:
        return None
    cons = qa.net_credit_conservative
    if s.status == "won":
        return round(cons * 100, 2)
    if s.status == "lost":
        return round(-(s.wing_width - cons) * 100, 2)
    return None


def compute_audit_stats(ledger: Ledger) -> dict:
    setups = ledger.setups
    audited = [s for s in setups if s.quote_audit is not None]
    deviations = [s.quote_audit.credit_deviation for s in audited]
    settled_pub = 0.0
    settled_cons = 0.0
    for s in audited:
        if s.settlement is not None and s.status in ("won", "lost"):
            settled_pub += s.settlement.final_pnl_per_spread
            cp = _conservative_pnl(s)
            if cp is not None:
                settled_cons += cp
    return {
        "total": len(setups),
        "audited": len(audited),
        "no_audit": len(setups) - len(audited),
        "collapsed_count": sum(1 for s in audited if s.quote_audit.any_collapsed),
        "conservative_nonpositive": sum(
            1 for s in audited if s.quote_audit.net_credit_conservative <= 0),
        "deviation_median": round(median(deviations), 4) if deviations else 0.0,
        "deviation_max": round(max(deviations), 4) if deviations else 0.0,
        "settled_pnl_published": round(settled_pub, 2),
        "settled_pnl_conservative": round(settled_cons, 2),
    }


def format_report(stats: dict) -> str:
    lines = [
        "=== Quote Audit Report ===",
        f"setups total          : {stats['total']}",
        f"  audited             : {stats['audited']}",
        f"  no_audit (legacy)   : {stats['no_audit']}",
        "",
        "--- 偏差面板 (audited only) ---",
        f"collapse legs setups  : {stats['collapsed_count']}",
        f"credit_deviation median: {stats['deviation_median']}",
        f"credit_deviation max   : {stats['deviation_max']}",
        "",
        "--- 保守门槛影响 ---",
        f"conservative <= 0     : {stats['conservative_nonpositive']}  (保守下不该发布)",
        "",
        "--- 盈利对比 (已结算) ---",
        f"published cum P&L     : {stats['settled_pnl_published']}",
        f"conservative cum P&L  : {stats['settled_pnl_conservative']}",
    ]
    return "\n".join(lines)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/ledger.json"
    ledger = LedgerStore(path).load()
    print(format_report(compute_audit_stats(ledger)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
