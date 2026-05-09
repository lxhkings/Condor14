"""SQLite-backed cache of daily OHLC bars per ticker."""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class BarRow:
    ticker: str
    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_bars (
    ticker  TEXT NOT NULL,
    bar_date TEXT NOT NULL,
    open    REAL NOT NULL,
    high    REAL NOT NULL,
    low     REAL NOT NULL,
    close   REAL NOT NULL,
    volume  INTEGER NOT NULL,
    PRIMARY KEY (ticker, bar_date)
);
CREATE INDEX IF NOT EXISTS idx_ticker_date ON daily_bars(ticker, bar_date);
"""


class DailyBarsCache:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert(self, rows: list[BarRow]) -> None:
        if not rows:
            return
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO daily_bars (ticker, bar_date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, bar_date) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume
                """,
                [
                    (r.ticker, r.bar_date.isoformat(), r.open, r.high, r.low, r.close, r.volume)
                    for r in rows
                ],
            )

    def read(self, ticker: str, *, start: date, end: date) -> list[BarRow]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT ticker, bar_date, open, high, low, close, volume
                FROM daily_bars
                WHERE ticker = ? AND bar_date BETWEEN ? AND ?
                ORDER BY bar_date ASC
                """,
                (ticker, start.isoformat(), end.isoformat()),
            )
            return [
                BarRow(
                    ticker=row[0],
                    bar_date=date.fromisoformat(row[1]),
                    open=row[2], high=row[3], low=row[4], close=row[5], volume=row[6],
                )
                for row in cur.fetchall()
            ]

    def latest_date(self, ticker: str) -> date | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT MAX(bar_date) FROM daily_bars WHERE ticker = ?",
                (ticker,),
            )
            row = cur.fetchone()
            if row is None or row[0] is None:
                return None
            return date.fromisoformat(row[0])


_EXPIRATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS option_expirations (
    ticker      TEXT NOT NULL,
    fetched_on  TEXT NOT NULL,
    expiration  TEXT NOT NULL,
    PRIMARY KEY (ticker, fetched_on, expiration)
);
"""


class ExpirationsCache:
    """Per-day cache of option expiration dates, sharing the daily-bars SQLite file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_EXPIRATIONS_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get(self, ticker: str, *, fetched_on: date) -> list[date] | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT expiration FROM option_expirations "
                "WHERE ticker = ? AND fetched_on = ? ORDER BY expiration",
                (ticker, fetched_on.isoformat()),
            )
            rows = cur.fetchall()
        if not rows:
            return None
        return [date.fromisoformat(r[0]) for r in rows]

    def put(self, ticker: str, *, fetched_on: date, expirations: list[date]) -> None:
        if not expirations:
            return
        with self._connect() as conn:
            # 先清空当日旧条目，再插新——保证 idempotent replace 语义。
            conn.execute(
                "DELETE FROM option_expirations WHERE ticker = ? AND fetched_on = ?",
                (ticker, fetched_on.isoformat()),
            )
            conn.executemany(
                "INSERT INTO option_expirations (ticker, fetched_on, expiration) VALUES (?, ?, ?)",
                [(ticker, fetched_on.isoformat(), e.isoformat()) for e in expirations],
            )
