"""Pipeline configuration: tickers, sector map, env-var names.

The 20-ticker MVP list is intentionally biased toward names with deep
weekly-options liquidity. Expansion to 100 happens in V2 only after the
4--6-week SEO observation gate (see spec §8.2) clears.
"""

TICKERS: list[str] = [
    "NVDA", "TSLA", "AAPL", "SPY",  "QQQ",
    "MSFT", "AMD",  "GOOGL", "META", "AMZN",
    "NFLX", "BABA", "AVGO",  "ORCL", "CRM",
    "ADBE", "INTC", "MU",    "COIN", "PLTR",
]

SECTORS: dict[str, str] = {
    # Semiconductors (5)
    "NVDA": "Semiconductors",
    "AMD":  "Semiconductors",
    "AVGO": "Semiconductors",
    "INTC": "Semiconductors",
    "MU":   "Semiconductors",
    # Mega-Cap Tech (7)
    "AAPL":  "Mega-Cap Tech",
    "MSFT":  "Mega-Cap Tech",
    "GOOGL": "Mega-Cap Tech",
    "META":  "Mega-Cap Tech",
    "AMZN":  "Mega-Cap Tech",
    "TSLA":  "Mega-Cap Tech",
    "NFLX":  "Mega-Cap Tech",
    # Software (4)
    "ORCL": "Software",
    "CRM":  "Software",
    "ADBE": "Software",
    "PLTR": "Software",
    # Index ETFs (2)
    "SPY": "Index ETFs",
    "QQQ": "Index ETFs",
    # International / High-Beta (2)
    "BABA": "Intl & High-Beta",
    "COIN": "Intl & High-Beta",
}
