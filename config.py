"""Pipeline configuration: tickers, sector map, env-var names.

18-ticker monitoring list focused on highest liquidity and premium.
"""

TICKERS: list[str] = [
    # Broad ETFs (大盘宽基 - 流动性天花板)
    "SPY", "QQQ", "IWM",
    # Semiconductors (半导体 - 权利金最丰厚)
    "SMH", "NVDA", "AMD", "AVGO", "TSM",
    # Mega-Cap Tech (核心科技权重 - 盘口极度紧密)
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "NFLX",
    # High-Beta / Crypto (高贝塔与加密概念 - 提款机)
    "COIN", "MSTR", "MARA",
]

SECTORS: dict[str, str] = {
    # Broad ETFs (大盘宽基)
    "SPY":  "Broad ETF",
    "QQQ":  "Broad ETF",
    "IWM":  "Broad ETF",
    # Semiconductors (半导体)
    "SMH":  "Sector ETF",
    "NVDA": "Semiconductors",
    "AMD":  "Semiconductors",
    "AVGO": "Semiconductors",
    "TSM":  "Semiconductors",
    # Mega-Cap Tech (核心科技权重)
    "AAPL":  "Mega-Cap Tech",
    "MSFT":  "Mega-Cap Tech",
    "GOOGL": "Mega-Cap Tech",
    "META":  "Mega-Cap Tech",
    "AMZN":  "Mega-Cap Tech",
    "TSLA":  "Mega-Cap Tech",
    "NFLX":  "Mega-Cap Tech",
    # High-Beta / Crypto (高贝塔与加密概念)
    "COIN": "High-Beta / Crypto",
    "MSTR": "High-Beta / Crypto",
    "MARA": "High-Beta / Crypto",
}
