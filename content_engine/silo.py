"""Same-sector internal link selector.

Per spec §5.5: each ticker page lists up to 4 same-sector peers,
alphabetically sorted, excluding the ticker itself.
"""

from collections import defaultdict

from config import SECTORS


def _by_sector() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for ticker, sector in SECTORS.items():
        grouped[sector].append(ticker)
    return grouped


def same_sector_peers(ticker: str, *, n: int = 4) -> list[str]:
    if ticker not in SECTORS:
        return []
    sector = SECTORS[ticker]
    pool = sorted(t for t in _by_sector()[sector] if t != ticker)
    return pool[:n]
