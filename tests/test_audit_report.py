from dataclasses import replace
from datetime import date

from ledger.schema import Ledger, QuoteAudit, Settlement, Setup
from audit_report import compute_audit_stats


def _base_setup(**kw) -> Setup:
    s = Setup(
        id="X", ticker="NVDA", sector="Semiconductors",
        start_date=date(2026, 5, 1), target_exit_date=date(2026, 5, 15),
        expiry_used=date(2026, 5, 15), underlying_at_open=200.0,
        atr14_at_open=5.0, sma20_at_open=195.0, vol_percentile_at_open=50,
        trend_bias="neutral", short_call_strike=215.0, long_call_strike=220.0,
        short_put_strike=185.0, long_put_strike=180.0, net_credit_at_open=2.0,
        wing_width=5.0, max_profit=2.0, max_loss=3.0,
        break_even_upper=217.0, break_even_lower=183.0,
        status="open", daily_marks=[], settlement=None,
    )
    return replace(s, **kw)


def _audit(pub, cons, collapsed=False) -> QuoteAudit:
    return QuoteAudit(legs={}, net_credit_published=pub,
                      net_credit_conservative=cons,
                      credit_deviation=round(pub - cons, 4),
                      any_collapsed=collapsed)


def test_compute_audit_stats_basic():
    won_settle = Settlement(settled_on=date(2026, 5, 15), final_underlying=200.0,
                            breached_side=None, final_pnl_per_spread=200.0)
    setups = [
        # 有审计、collapse、won：发布 2.0 保守 1.0
        _base_setup(id="A", status="won", settlement=won_settle,
                    quote_audit=_audit(2.0, 1.0, collapsed=True)),
        # 有审计、保守<=0：保守门槛会刷掉
        _base_setup(id="B", status="open",
                    quote_audit=_audit(0.5, -0.2, collapsed=True)),
        # 无审计（旧单）
        _base_setup(id="C", status="open", quote_audit=None),
    ]
    stats = compute_audit_stats(Ledger(setups=setups, skipped=[]))
    assert stats["total"] == 3
    assert stats["audited"] == 2
    assert stats["no_audit"] == 1
    assert stats["collapsed_count"] == 2
    assert stats["conservative_nonpositive"] == 1  # B
    # 偏差：A=1.0, B=0.7 -> max 1.0
    assert stats["deviation_max"] == 1.0
    # 已结算保守盈利：A won -> +1.0*100=100；published A -> +200
    assert stats["settled_pnl_published"] == 200.0
    assert stats["settled_pnl_conservative"] == 100.0
