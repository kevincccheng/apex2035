# core/prices.py — live price fetching via yfinance with caching
import time
import datetime
import yfinance as yf
import streamlit as st
from config import TICKER_MAP, PRICE_CACHE_S

_HKT = datetime.timezone(datetime.timedelta(hours=8))

def _now_hkt():
    return datetime.datetime.now(_HKT).strftime("%Y-%m-%d %H:%M HKT")

# ── FX rate ───────────────────────────────────────────────────────
@st.cache_data(ttl=PRICE_CACHE_S)
def get_hkd_usd_rate() -> float:
    """Live HKD/USD rate from yfinance."""
    try:
        tk = yf.Ticker("USDHKD=X")
        hist = tk.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 7.834  # fallback

# ── Single ticker ─────────────────────────────────────────────────
@st.cache_data(ttl=PRICE_CACHE_S)
def get_price(ticker: str) -> dict:
    """
    Returns {"price": float, "currency": str, "timestamp": str, "error": str|None}
    Handles BRK/B → BRK-B mapping automatically.
    """
    if ticker in TICKER_MAP:
        mapped = TICKER_MAP[ticker]
        if mapped is None:
            return {"price": None, "currency": None,
                    "timestamp": None, "error": "manual_price"}
        ticker = mapped

    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info
        price = info.last_price
        currency = getattr(info, "currency", "USD")
        if price and price > 0:
            return {
                "price":     round(float(price), 4),
                "currency":  currency,
                "timestamp": _now_hkt(),
                "error":     None,
            }
        # fallback: last close from history
        hist = tk.history(period="2d")
        if not hist.empty:
            return {
                "price":     round(float(hist["Close"].iloc[-1]), 4),
                "currency":  currency,
                "timestamp": _now_hkt() + " (prev close)",
                "error":     None,
            }
    except Exception as e:
        return {"price": None, "currency": None,
                "timestamp": None, "error": str(e)}

    return {"price": None, "currency": None,
            "timestamp": None, "error": "no_data"}


# ── Batch fetch ───────────────────────────────────────────────────
@st.cache_data(ttl=PRICE_CACHE_S)
def get_prices_batch(tickers: tuple) -> dict:
    """
    Fetches prices for a list of tickers in one yfinance call.
    Returns dict: {ticker: {"price": float, "currency": str, ...}}
    tickers must be a tuple (hashable for Streamlit cache).
    """
    results = {}
    # Map tickers
    mapped = {}
    for t in tickers:
        m = TICKER_MAP.get(t, t)
        if m is None:
            results[t] = {"price": None, "currency": None,
                          "timestamp": None, "error": "manual_price"}
        else:
            mapped[t] = m

    if not mapped:
        return results

    try:
        raw_tickers = list(mapped.values())
        data = yf.download(
            raw_tickers,
            period="2d",
            auto_adjust=True,
            progress=False,
            threads=True,
            timeout=30,
        )
        close = data["Close"] if "Close" in data else data

        for orig, mapped_t in mapped.items():
            try:
                if len(raw_tickers) == 1:
                    price = float(close.iloc[-1])
                else:
                    price = float(close[mapped_t].dropna().iloc[-1])
                results[orig] = {
                    "price":     round(price, 4),
                    "currency":  "HKD" if orig.endswith(".HK") else "USD",
                    "timestamp": _now_hkt(),
                    "error":     None,
                }
            except Exception as e:
                results[orig] = {"price": None, "currency": None,
                                 "timestamp": None, "error": str(e)}
    except Exception as e:
        # fallback: individual fetches
        for orig in mapped:
            results[orig] = get_price(orig)

    return results
