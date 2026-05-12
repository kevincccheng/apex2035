# config.py  —  Project Apex 2035
# All positions pre-seeded from May 4, 2026 portfolio snapshot
# Edit barbell_class here to override classification

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

USE_LSEG = bool(os.getenv("EDP_API_KEY"))

# ── Project targets ───────────────────────────────────────────────
PROJECT_NAME   = "Project Apex 2035"
TARGET_5X_USD  = 13_350_000   # Garden Terrace target
TARGET_10X_USD = 26_700_000   # Maximum buffer by 2042
BASE_DATE      = "2026-05-04"
HKD_USD_RATE   = 7.834        # Refreshed live at runtime; fallback only

# ── Compliance rules (edit here — no code changes needed) ─────────
COMPLIANCE = {
    "banned_sectors":        ["Banking", "Insurance"],
    "min_hold_days_stock":   30,
    "min_hold_days_gold":    90,
    "etf_hold_exempt":       True,   # ETFs skip holding period
    "us_div_withholding":    0.30,   # 30% withholding tax on US dividends
    "hk_capital_gains_tax":  0.00,   # 0% — HK tax resident
}

# ── Price source ──────────────────────────────────────────────────
PRICE_SOURCE  = "yfinance"   # "yfinance" | "lseg" — swap here only
PRICE_CACHE_S = 3600         # cache prices for 1 hour (manual refresh always available)

# ── Google Sheets ─────────────────────────────────────────────────
GSHEET_NAME            = "Apex2035_Master"
SHEET_HOLDINGS         = "Holdings_Master"
SHEET_TRADES           = "Trades_Ledger"
SHEET_CONFIG           = "Config"
SHEET_BROKER_SNAPSHOTS = "Broker_Snapshots"

# ── Brokers ───────────────────────────────────────────────────────
BROKERS = ["Schwab", "IBKR", "Futu", "HSBC", "BOC", "Webull", "Moomoo", "Citi"]
ACTIVE_BROKERS  = ["Schwab", "IBKR", "Futu", "Moomoo"]   # delta upload supported
LEGACY_BROKERS  = ["HSBC", "BOC", "Webull", "Citi"]       # manual snapshot

# ── Currency config ───────────────────────────────────────────────
REPORT_CURRENCIES = ["USD", "HKD"]
DEFAULT_CURRENCY  = "USD"

# ═══════════════════════════════════════════════════════════════════
# MASTER POSITIONS — seeded from May 4, 2026 session
# Fields: ticker, name, region, sector, barbell_class, ccy,
#         brokers: [{broker, shares, avg_cost_local}]
# barbell_class: CORE | TACTICAL | SPECULATIVE
# ═══════════════════════════════════════════════════════════════════

INITIAL_POSITIONS = [

    # ── CORE — US broad market & quality compounders ───────────────
    {
        "ticker": "MSFT", "name": "Microsoft", "region": "US",
        "sector": "Tech — Cloud", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 457.24, "avg_cost_local": 413.75}],
    },
    {
        "ticker": "VOO", "name": "Vanguard S&P 500 ETF", "region": "US",
        "sector": "ETF — US Broad", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": 102.56, "avg_cost_local": 218.46}],
    },
    {
        "ticker": "BRK/B", "name": "Berkshire Hathaway B", "region": "US",
        "sector": "Financials — Conglomerate", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 120,   "avg_cost_local": 484.01},
            {"broker": "Citi",   "shares": 104,   "avg_cost_local": 479.20},
        ],
    },
    {
        "ticker": "GLD", "name": "SPDR Gold Shares", "region": "US",
        "sector": "Commodities — Gold", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 50,  "avg_cost_local": 190.00},
            {"broker": "IBKR",   "shares": 100, "avg_cost_local": 185.01},
        ],
    },
    {
        "ticker": "IAU", "name": "iShares Gold Trust", "region": "US",
        "sector": "Commodities — Gold", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 100, "avg_cost_local": 37.38},
            {"broker": "Moomoo", "shares": 80,  "avg_cost_local": 77.61},
        ],
    },
    {
        "ticker": "SLV", "name": "iShares Silver Trust", "region": "US",
        "sector": "Commodities — Silver", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 200, "avg_cost_local": 31.07},
            {"broker": "Moomoo", "shares": 100, "avg_cost_local": 46.93},
        ],
    },
    {
        "ticker": "ETN", "name": "Eaton Corp", "region": "US",
        "sector": "Industrials", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": 100, "avg_cost_local": 357.81}],
    },
    {
        "ticker": "GE", "name": "GE Aerospace", "region": "US",
        "sector": "Industrials", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 100, "avg_cost_local": 283.38}],
    },
    {
        "ticker": "XOM", "name": "Exxon Mobil", "region": "US",
        "sector": "Energy", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": 211.62, "avg_cost_local": 46.44}],
    },
    {
        "ticker": "VDE", "name": "Vanguard Energy ETF", "region": "US",
        "sector": "ETF — Energy", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 104.33, "avg_cost_local": 67.86},
            {"broker": "IBKR",   "shares": 156.48, "avg_cost_local": 47.55},
        ],
    },
    {
        "ticker": "ITA", "name": "iShares Aerospace & Defense", "region": "US",
        "sector": "ETF — Defense", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 100.97, "avg_cost_local": 80.28},
            {"broker": "IBKR",   "shares": 102.49, "avg_cost_local": 84.06},
        ],
    },
    {
        "ticker": "VTV", "name": "Vanguard Value ETF", "region": "US",
        "sector": "ETF — US Value", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 103.15, "avg_cost_local": 132.52}],
    },
    {
        "ticker": "SCHD", "name": "Schwab US Dividend ETF", "region": "US",
        "sector": "ETF — Dividend", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": 151.23, "avg_cost_local": 26.81}],
    },
    {
        "ticker": "VT", "name": "Vanguard Total World ETF", "region": "US",
        "sector": "ETF — Global", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 51.33, "avg_cost_local": 79.28}],
    },
    {
        "ticker": "VNQ", "name": "Vanguard Real Estate ETF", "region": "US",
        "sector": "ETF — Real Estate", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 40, "avg_cost_local": 92.31}],
    },
    {
        "ticker": "MOAT", "name": "VanEck Wide Moat ETF", "region": "US",
        "sector": "ETF — Quality", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 20, "avg_cost_local": 88.82}],
    },
    {
        "ticker": "CEG", "name": "Constellation Energy", "region": "US",
        "sector": "Utilities — Nuclear", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 20, "avg_cost_local": 288.83}],
    },
    {
        "ticker": "DBA", "name": "Invesco DB Agriculture", "region": "US",
        "sector": "ETF — Commodities", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 539.29, "avg_cost_local": 13.98}],
    },
    {
        "ticker": "USO", "name": "US Oil Fund", "region": "US",
        "sector": "ETF — Commodities", "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 125, "avg_cost_local": 22.40}],
    },
    # HK Core
    {
        "ticker": "2800.HK", "name": "Tracker Fund of HK", "region": "HK",
        "sector": "ETF — HK Broad", "barbell_class": "CORE", "ccy": "HKD",
        "brokers": [
            {"broker": "HSBC", "shares": 15000, "avg_cost_local": 27.61},
            {"broker": "IBKR", "shares": 1000,  "avg_cost_local": 26.78},
            {"broker": "Futu", "shares": 500,   "avg_cost_local": 25.00},
        ],
    },
    {
        "ticker": "0388.HK", "name": "HKEX", "region": "HK",
        "sector": "Financial Exchange", "barbell_class": "CORE", "ccy": "HKD",
        "brokers": [
            {"broker": "HSBC", "shares": 800, "avg_cost_local": 342.62},
            {"broker": "IBKR", "shares": 100, "avg_cost_local": 436.20},
            {"broker": "Futu", "shares": 400, "avg_cost_local": 401.20},
        ],
    },
    {
        "ticker": "3437.HK", "name": "BOS CSOE HIDV ETF", "region": "HK",
        "sector": "ETF — HK Dividend", "barbell_class": "CORE", "ccy": "HKD",
        "brokers": [{"broker": "BOC", "shares": 2000, "avg_cost_local": 10.21}],
    },
    {
        "ticker": "3110.HK", "name": "GX HS HIGHDIV ETF", "region": "HK",
        "sector": "ETF — HK Dividend", "barbell_class": "CORE", "ccy": "HKD",
        "brokers": [{"broker": "BOC", "shares": 1000, "avg_cost_local": 30.81}],
    },
    {
        "ticker": "0808.HK", "name": "Prosperity REIT", "region": "HK",
        "sector": "REIT", "barbell_class": "CORE", "ccy": "HKD",
        "brokers": [{"broker": "BOC", "shares": 10000, "avg_cost_local": 1.37}],
    },
    {
        "ticker": "2778.HK", "name": "Champion REIT", "region": "HK",
        "sector": "REIT", "barbell_class": "CORE", "ccy": "HKD",
        "brokers": [{"broker": "BOC", "shares": 12000, "avg_cost_local": 2.03}],
    },
    {
        "ticker": "3067.HK", "name": "iShares Hang Seng Tech ETF", "region": "HK",
        "sector": "ETF — HK Tech", "barbell_class": "CORE", "ccy": "HKD",
        "brokers": [
            {"broker": "HSBC", "shares": 3300, "avg_cost_local": 11.96},
            {"broker": "IBKR", "shares": 1000, "avg_cost_local": 11.57},
        ],
    },

    # ── TACTICAL — high conviction, active positions ───────────────
    {
        "ticker": "GOOGL", "name": "Alphabet A", "region": "US",
        "sector": "Tech — Internet", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 177.01, "avg_cost_local": 217.73},
            {"broker": "IBKR",   "shares": 62.31,  "avg_cost_local": 154.53},
        ],
    },
    {
        "ticker": "GOOG", "name": "Alphabet C", "region": "US",
        "sector": "Tech — Internet", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": 23.13, "avg_cost_local": 151.15}],
    },
    {
        "ticker": "AMZN", "name": "Amazon", "region": "US",
        "sector": "Tech — E-commerce", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 268.68, "avg_cost_local": 213.79},
            {"broker": "IBKR",   "shares": 56.57,  "avg_cost_local": 180.13},
            {"broker": "Moomoo", "shares": 100,    "avg_cost_local": 229.38},
        ],
    },
    {
        "ticker": "META", "name": "Meta Platforms", "region": "US",
        "sector": "Tech — Social Media", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 128,   "avg_cost_local": 627.57},
            {"broker": "IBKR",   "shares": 40.06, "avg_cost_local": 600.54},
            {"broker": "Moomoo", "shares": 25,    "avg_cost_local": 749.10},
        ],
    },
    {
        "ticker": "AAPL", "name": "Apple", "region": "US",
        "sector": "Tech — Consumer", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 154.35, "avg_cost_local": 172.60}],
    },
    {
        "ticker": "NVDA", "name": "NVIDIA", "region": "US",
        "sector": "Tech — Semiconductors", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 30,   "avg_cost_local": 113.00},
            {"broker": "IBKR",   "shares": 15.07,"avg_cost_local": 168.22},
            {"broker": "Webull", "shares": 1.35, "avg_cost_local": 34.797},
        ],
    },
    {
        "ticker": "AMD", "name": "AMD", "region": "US",
        "sector": "Tech — Semiconductors", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 100, "avg_cost_local": 260.40}],
    },
    {
        "ticker": "MU", "name": "Micron Technology", "region": "US",
        "sector": "Tech — Semiconductors", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 30, "avg_cost_local": 418.00}],
    },
    {
        "ticker": "TSM", "name": "TSMC ADR", "region": "US",
        "sector": "Tech — Semiconductors", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 25, "avg_cost_local": 172.64}],
    },
    {
        "ticker": "TSLA", "name": "Tesla", "region": "US",
        "sector": "EV — Auto", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 105, "avg_cost_local": 246.81},
            {"broker": "IBKR",   "shares": 10,  "avg_cost_local": 248.90},
        ],
    },
    {
        "ticker": "PLTR", "name": "Palantir", "region": "US",
        "sector": "Tech — AI", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 165, "avg_cost_local": 67.12}],
    },
    {
        "ticker": "QQQM", "name": "Invesco Nasdaq 100 ETF", "region": "US",
        "sector": "ETF — US Tech", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [
            {"broker": "Schwab", "shares": 120,  "avg_cost_local": 201.08},
            {"broker": "IBKR",   "shares": 8.47, "avg_cost_local": 190.96},
        ],
    },
    {
        "ticker": "VFH", "name": "Vanguard Financials ETF", "region": "US",
        "sector": "ETF — Financials", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": 126.83, "avg_cost_local": 105.04}],
    },
    {
        "ticker": "VGT", "name": "Vanguard Info Tech ETF", "region": "US",
        "sector": "ETF — US Tech", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": 23.41, "avg_cost_local": 68.99}],
    },
    {
        "ticker": "SCHG", "name": "Schwab US Growth ETF", "region": "US",
        "sector": "ETF — US Growth", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 200, "avg_cost_local": 29.84}],
    },
    # HK/China Tactical
    {
        "ticker": "0700.HK", "name": "Tencent", "region": "China",
        "sector": "Tech — Internet", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [
            {"broker": "HSBC",   "shares": 200, "avg_cost_local": 501.09},
            {"broker": "IBKR",   "shares": 200, "avg_cost_local": 639.42},
            {"broker": "BOC",    "shares": 200, "avg_cost_local": 348.08},
            {"broker": "Webull", "shares": 800, "avg_cost_local": 535.413},
        ],
    },
    {
        "ticker": "9988.HK", "name": "Alibaba", "region": "China",
        "sector": "Tech — E-commerce", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [
            {"broker": "HSBC",   "shares": 2700, "avg_cost_local": 94.27},
            {"broker": "IBKR",   "shares": 700,  "avg_cost_local": 142.95},
            {"broker": "Futu",   "shares": 300,  "avg_cost_local": 151.00},
            {"broker": "Webull", "shares": 100, "avg_cost_local": 153.200},
        ],
    },
    {
        "ticker": "9618.HK", "name": "JD.com", "region": "China",
        "sector": "Tech — E-commerce", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [{"broker": "Webull", "shares": 100, "avg_cost_local": 113.800}],
    },
    {
        "ticker": "3690.HK", "name": "Meituan", "region": "China",
        "sector": "Tech — On-demand", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [
            {"broker": "HSBC", "shares": 500, "avg_cost_local": 138.10},
            {"broker": "Futu", "shares": 200, "avg_cost_local": 95.05},
        ],
    },
    {
        "ticker": "3750.HK", "name": "CATL", "region": "China",
        "sector": "EV — Batteries", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [{"broker": "Futu", "shares": 100, "avg_cost_local": 610.00}],
    },
    {
        "ticker": "0981.HK", "name": "SMIC", "region": "China",
        "sector": "Semiconductors", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [{"broker": "Futu", "shares": 1000, "avg_cost_local": 64.58}],
    },
    {
        "ticker": "1211.HK", "name": "BYD Company H", "region": "China",
        "sector": "EV — Auto", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [{"broker": "HSBC", "shares": 500, "avg_cost_local": 137.55}],
    },
    {
        "ticker": "0241.HK", "name": "Ali Health", "region": "China",
        "sector": "Healthcare", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [{"broker": "HSBC", "shares": 6000, "avg_cost_local": 4.27}],
    },
    {
        "ticker": "0386.HK", "name": "Sinopec H", "region": "China",
        "sector": "Energy", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [{"broker": "IBKR", "shares": 6000, "avg_cost_local": 4.13}],
    },
    {
        "ticker": "2846.HK", "name": "iShares CSI 300 ETF", "region": "China",
        "sector": "ETF — China", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [{"broker": "IBKR", "shares": 100, "avg_cost_local": 29.64}],
    },
    {
        "ticker": "0066.HK", "name": "MTR Corp", "region": "HK",
        "sector": "Infrastructure", "barbell_class": "TACTICAL", "ccy": "HKD",
        "brokers": [
            {"broker": "HSBC", "shares": 10000, "avg_cost_local": 39.96},
            {"broker": "BOC",  "shares": 10000, "avg_cost_local": 45.00},
        ],
    },
    {
        "ticker": "TEM", "name": "Tempus AI", "region": "US",
        "sector": "Tech — AI Healthcare", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 120, "avg_cost_local": 56.11}],
    },
    {
        "ticker": "PYPL", "name": "PayPal", "region": "US",
        "sector": "Fintech", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 150, "avg_cost_local": 71.41}],
    },
    {
        "ticker": "OSCR", "name": "Oscar Health", "region": "US",
        "sector": "Healthcare", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 200, "avg_cost_local": 15.32}],
    },
    {
        "ticker": "GRAB", "name": "Grab Holdings", "region": "SEA",
        "sector": "Tech — Rideshare", "barbell_class": "TACTICAL", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 400, "avg_cost_local": 3.64}],
    },

    # ── SPECULATIVE — asymmetric bets, high beta ───────────────────
    {
        "ticker": "APLD", "name": "Applied Digital Corp", "region": "US",
        "sector": "Tech — AI Infra", "barbell_class": "SPECULATIVE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 300, "avg_cost_local": 9.05}],
    },
    {
        "ticker": "SOFI", "name": "SoFi Technologies", "region": "US",
        "sector": "Fintech", "barbell_class": "SPECULATIVE", "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": 100, "avg_cost_local": 6.62}],
    },
    {
        "ticker": "SYM", "name": "Symbotic", "region": "US",
        "sector": "Tech — Robotics", "barbell_class": "SPECULATIVE", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 100, "avg_cost_local": 47.96}],
    },
    {
        "ticker": "YINN", "name": "Direxion China Bull 3X", "region": "US",
        "sector": "ETF — Leveraged", "barbell_class": "SPECULATIVE", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 440, "avg_cost_local": 44.86}],
    },
    {
        "ticker": "BITX", "name": "2x Bitcoin Strategy ETF", "region": "US",
        "sector": "ETF — Crypto", "barbell_class": "SPECULATIVE", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 200, "avg_cost_local": 19.50}],
    },
    {
        "ticker": "EZBC", "name": "Franklin Bitcoin ETF", "region": "US",
        "sector": "ETF — Crypto", "barbell_class": "SPECULATIVE", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 50, "avg_cost_local": 45.55}],
    },
    {
        "ticker": "SQQQ", "name": "ProShares Short QQQ", "region": "US",
        "sector": "ETF — Inverse", "barbell_class": "SPECULATIVE", "ccy": "USD",
        "brokers": [{"broker": "Moomoo", "shares": 40, "avg_cost_local": 75.31}],
    },
    {
        "ticker": "1787.HK", "name": "SD Gold", "region": "China",
        "sector": "Commodities — Gold", "barbell_class": "SPECULATIVE", "ccy": "HKD",
        "brokers": [{"broker": "Futu", "shares": 500, "avg_cost_local": 35.46}],
    },
    {
        "ticker": "2400.HK", "name": "XD Inc", "region": "China",
        "sector": "Tech — Gaming", "barbell_class": "SPECULATIVE", "ccy": "HKD",
        "brokers": [{"broker": "Moomoo", "shares": 200, "avg_cost_local": 86.80}],
    },
    {
        "ticker": "2498.HK", "name": "RoboSense", "region": "China",
        "sector": "Tech — Robotics", "barbell_class": "SPECULATIVE", "ccy": "HKD",
        "brokers": [{"broker": "Moomoo", "shares": 100, "avg_cost_local": 45.80}],
    },
    {
        "ticker": "9880.HK", "name": "UBTECH Robotics", "region": "China",
        "sector": "Tech — Robotics", "barbell_class": "SPECULATIVE", "ccy": "HKD",
        "brokers": [{"broker": "Moomoo", "shares": 50, "avg_cost_local": 133.30}],
    },
    # ── SHORT CALLS (options) — negative shares = short position ─────
    # shares=-100 = 1 short contract; avg_cost_local = premium received per share
    {
        "ticker": "NVDA-C200-DEC26", "name": "Short Call NVDA $200 Dec-2026",
        "region": "US", "sector": "Options — Short Call", "barbell_class": "TACTICAL",
        "ccy": "USD",
        "brokers": [{"broker": "IBKR", "shares": -100, "avg_cost_local": 27.10}],
    },
    {
        "ticker": "MSFT-C440-MAY26", "name": "Short Call MSFT $440 May-2026",
        "region": "US", "sector": "Options — Short Call", "barbell_class": "TACTICAL",
        "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": -100, "avg_cost_local": 15.99}],
    },
    {
        "ticker": "APLD-C32-MAY26", "name": "Short Call APLD $32 May-2026",
        "region": "US", "sector": "Options — Short Call", "barbell_class": "TACTICAL",
        "ccy": "USD",
        "brokers": [{"broker": "Schwab", "shares": -100, "avg_cost_local": 3.61}],
    },

    # Citi structured note — fixed income bucket
    {
        "ticker": "STRUCT-CITI", "name": "Citi Dual Ccy Note USD/SGD/CHF Jun-2029",
        "region": "Other", "sector": "Fixed Income — Structured",
        "barbell_class": "CORE", "ccy": "USD",
        "brokers": [{"broker": "Citi", "shares": 1, "avg_cost_local": 50000}],
    },
]

# ── Ticker format map for yfinance ───────────────────────────────
# yfinance uses slightly different formats for some tickers
TICKER_MAP = {
    "BRK/B":          "BRK-B",
    "STRUCT-CITI":    None,              # no live price, mark manually
    "9618.HK":        "9618.HK",
    # Short calls — OCC option ticker format for yfinance
    "NVDA-C200-DEC26": "NVDA261218C00200000",
    "MSFT-C440-MAY26": "MSFT260522C00440000",
    "APLD-C32-MAY26":  "APLD260522C00032000",
}
