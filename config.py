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
    # --- Expansion to 50 (liquidity-curated) ---
    # Broad / Sector ETFs (宽基与板块 ETF - 盘口紧)
    "DIA", "GLD", "SLV", "TLT", "XLF", "XLE", "EEM", "GDX",
    # Semiconductors (半导体)
    "MU", "INTC", "QCOM", "ARM", "MRVL", "SMCI",
    # Software / Internet (软件与互联网)
    "PLTR", "CRM", "ORCL", "UBER", "SHOP", "SNOW",
    # Financials (金融)
    "JPM", "BAC", "GS", "V",
    # Consumer / Industrials (消费与工业)
    "DIS", "BA", "COST", "NKE",
    # Energy (能源)
    "XOM", "OXY",
    # High-Beta / Crypto (高贝塔与加密)
    "HOOD", "RIOT",
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
    # --- Expansion to 50 ---
    # Broad / Sector ETFs
    "DIA":  "Broad ETF",
    "GLD":  "Sector ETF",
    "SLV":  "Sector ETF",
    "TLT":  "Sector ETF",
    "XLF":  "Sector ETF",
    "XLE":  "Sector ETF",
    "EEM":  "Sector ETF",
    "GDX":  "Sector ETF",
    # Semiconductors
    "MU":   "Semiconductors",
    "INTC": "Semiconductors",
    "QCOM": "Semiconductors",
    "ARM":  "Semiconductors",
    "MRVL": "Semiconductors",
    "SMCI": "Semiconductors",
    # Software / Internet
    "PLTR": "Software / Internet",
    "CRM":  "Software / Internet",
    "ORCL": "Software / Internet",
    "UBER": "Software / Internet",
    "SHOP": "Software / Internet",
    "SNOW": "Software / Internet",
    # Financials
    "JPM":  "Financials",
    "BAC":  "Financials",
    "GS":   "Financials",
    "V":    "Financials",
    # Consumer / Industrials
    "DIS":  "Consumer / Industrials",
    "BA":   "Consumer / Industrials",
    "COST": "Consumer / Industrials",
    "NKE":  "Consumer / Industrials",
    # Energy
    "XOM":  "Energy",
    "OXY":  "Energy",
    # High-Beta / Crypto
    "HOOD": "High-Beta / Crypto",
    "RIOT": "High-Beta / Crypto",
}
