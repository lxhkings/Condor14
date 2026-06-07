"""Ledger data model and JSON (de)serialization.

Schema version 1. The on-disk JSON format mirrors the dataclasses below
with two adjustments:
    - dates serialize as ISO 8601 strings
    - datetimes serialize with timezone suffix

`ledger_to_json` produces stable, sorted, indented output suitable for
human-readable git diffs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Literal


SCHEMA_VERSION = 1

TrendBias = Literal["bullish", "bearish", "neutral"]
SetupStatus = Literal["open", "won", "lost"]
BreachedSide = Literal["upper", "lower"]


@dataclass(frozen=True)
class DailyMark:
    date: date
    underlying_close: float
    breached_short: bool


@dataclass(frozen=True)
class Settlement:
    settled_on: date
    final_underlying: float
    breached_side: BreachedSide | None
    final_pnl_per_spread: float


@dataclass(frozen=True)
class OptionAnalyticsSnapshot:
    short_call_exercise_prob: float
    short_put_exercise_prob: float
    implied_pop: float
    short_call_iv: float
    short_call_hv: float
    vol_premium: float
    iv_gt_hv: bool


@dataclass(frozen=True)
class QuoteAudit:
    legs: dict[str, dict]
    net_credit_published: float
    net_credit_conservative: float
    credit_deviation: float
    any_collapsed: bool


@dataclass(frozen=True)
class Setup:
    id: str
    ticker: str
    sector: str
    start_date: date
    target_exit_date: date
    expiry_used: date
    underlying_at_open: float
    atr14_at_open: float
    sma20_at_open: float
    vol_percentile_at_open: int
    trend_bias: TrendBias
    short_call_strike: float
    long_call_strike: float
    short_put_strike: float
    long_put_strike: float
    net_credit_at_open: float
    wing_width: float
    max_profit: float
    max_loss: float
    break_even_upper: float
    break_even_lower: float
    status: SetupStatus
    daily_marks: list[DailyMark]
    settlement: Settlement | None
    atr60_at_open: float = 0.0
    analytics_at_open: OptionAnalyticsSnapshot | None = None
    quote_audit: QuoteAudit | None = None


@dataclass(frozen=True)
class SkippedEntry:
    ticker: str
    date: date
    reason: str


@dataclass
class Ledger:
    setups: list[Setup] = field(default_factory=list)
    skipped: list[SkippedEntry] = field(default_factory=list)
    site_launch_date: date | None = None
    first_settlement_date: date | None = None
    last_run: datetime | None = None


def _encode(obj):
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"unencodable: {type(obj)}")


def ledger_to_json(ledger: Ledger) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "site_launch_date": ledger.site_launch_date,
        "first_settlement_date": ledger.first_settlement_date,
        "last_run": ledger.last_run,
        "setups": [asdict(s) for s in ledger.setups],
        "skipped": [asdict(s) for s in ledger.skipped],
    }
    return json.dumps(payload, indent=2, sort_keys=False, default=_encode)


def _parse_date(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _parse_dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def ledger_from_json(blob: str) -> Ledger:
    data = json.loads(blob)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {data.get('schema_version')}")

    def _setup(d: dict) -> Setup:
        marks = [
            DailyMark(
                date=_parse_date(m["date"]),
                underlying_close=m["underlying_close"],
                breached_short=m["breached_short"],
            )
            for m in d["daily_marks"]
        ]
        sett = None
        if d["settlement"] is not None:
            sd = d["settlement"]
            sett = Settlement(
                settled_on=_parse_date(sd["settled_on"]),
                final_underlying=sd["final_underlying"],
                breached_side=sd["breached_side"],
                final_pnl_per_spread=sd["final_pnl_per_spread"],
            )
        analytics = None
        ad = d.get("analytics_at_open")
        if ad is not None:
            analytics = OptionAnalyticsSnapshot(
                short_call_exercise_prob=ad["short_call_exercise_prob"],
                short_put_exercise_prob=ad["short_put_exercise_prob"],
                implied_pop=ad["implied_pop"],
                short_call_iv=ad["short_call_iv"],
                short_call_hv=ad["short_call_hv"],
                vol_premium=ad["vol_premium"],
                iv_gt_hv=ad["iv_gt_hv"],
            )
        qa = d.get("quote_audit")
        quote_audit = None
        if qa is not None:
            quote_audit = QuoteAudit(
                legs=qa["legs"],
                net_credit_published=qa["net_credit_published"],
                net_credit_conservative=qa["net_credit_conservative"],
                credit_deviation=qa["credit_deviation"],
                any_collapsed=qa["any_collapsed"],
            )
        return Setup(
            id=d["id"], ticker=d["ticker"], sector=d["sector"],
            start_date=_parse_date(d["start_date"]),
            target_exit_date=_parse_date(d["target_exit_date"]),
            expiry_used=_parse_date(d["expiry_used"]),
            underlying_at_open=d["underlying_at_open"],
            atr14_at_open=d["atr14_at_open"],
            sma20_at_open=d["sma20_at_open"],
            vol_percentile_at_open=d.get(
                "vol_percentile_at_open", d.get("iv_percentile_at_open", 50)
            ),
            trend_bias=d["trend_bias"],
            short_call_strike=d["short_call_strike"],
            long_call_strike=d["long_call_strike"],
            short_put_strike=d["short_put_strike"],
            long_put_strike=d["long_put_strike"],
            net_credit_at_open=d["net_credit_at_open"],
            wing_width=d["wing_width"],
            max_profit=d["max_profit"],
            max_loss=d["max_loss"],
            break_even_upper=d["break_even_upper"],
            break_even_lower=d["break_even_lower"],
            status=d["status"],
            daily_marks=marks,
            settlement=sett,
            atr60_at_open=d.get("atr60_at_open", 0.0),
            analytics_at_open=analytics,
            quote_audit=quote_audit,
        )

    setups = [_setup(s) for s in data.get("setups", [])]
    skipped = [
        SkippedEntry(ticker=s["ticker"], date=_parse_date(s["date"]), reason=s["reason"])
        for s in data.get("skipped", [])
    ]
    return Ledger(
        setups=setups,
        skipped=skipped,
        site_launch_date=_parse_date(data.get("site_launch_date")),
        first_settlement_date=_parse_date(data.get("first_settlement_date")),
        last_run=_parse_dt(data.get("last_run")),
    )
