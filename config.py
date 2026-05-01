"""Pipeline configuration: tickers, sector map, env-var names.

30-ticker monitoring list covering broad ETFs, mega-cap tech, semis,
high-beta/crypto, growth, metals/bonds, and financial/cyclical sectors.
"""

TICKERS: list[str] = [
    # Broad ETFs (大盘宽基)
    "SPY", "QQQ", "IWM",
    # Sector ETFs (行业风向标)
    "SMH", "ARKK",
    # Semiconductors (高波动半导体)
    "NVDA", "AMD", "AVGO", "MU", "TSM",
    # Mega-Cap Tech (核心科技权重)
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "NFLX",
    # High-Beta / Crypto (高贝塔与加密概念)
    "COIN", "MSTR", "MARA",
    # Growth / Software (高波动成长股)
    "PLTR", "ARM", "UBER", "CRWD",
    # Metals / Bonds (避险与对冲)
    "GLD", "SLV", "TLT",
    # Financial / Cyclical (金融与周期基石)
    "JPM", "DIS", "XLE",
]

SECTORS: dict[str, str] = {
    # Broad ETFs (大盘宽基)
    "SPY":  "Broad ETF",
    "QQQ":  "Broad ETF",
    "IWM":  "Broad ETF",
    # Sector ETFs (行业风向标)
    "SMH":  "Sector ETF",
    "ARKK": "Sector ETF",
    # Semiconductors (高波动半导体)
    "NVDA": "Semiconductors",
    "AMD":  "Semiconductors",
    "AVGO": "Semiconductors",
    "MU":   "Semiconductors",
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
    # Growth / Software (高波动成长股)
    "PLTR": "Growth",
    "ARM":  "Growth",
    "UBER": "Growth",
    "CRWD": "Growth",
    # Metals / Bonds (避险与对冲)
    "GLD": "Metals / Bonds",
    "SLV": "Metals / Bonds",
    "TLT": "Metals / Bonds",
    # Financial / Cyclical (金融与周期基石)
    "JPM": "Financial / Cyclical",
    "DIS": "Financial / Cyclical",
    "XLE": "Financial / Cyclical",
}
