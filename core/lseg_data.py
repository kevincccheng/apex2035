# core/lseg_data.py — LSEG Desktop Session integration (local only)
# Requires Refinitiv Workspace to be running on this PC (localhost:9000).
# On Streamlit Cloud or without Workspace: all functions return {} / False safely.
# DO NOT add LSEG credentials here — desktop session only, no platform/RDP.

import streamlit as st


def _import_lseg_lib():
    """Return the first available LSEG/Refinitiv data module, or None."""
    for lib_name in ("lseg.data", "refinitiv.data"):
        try:
            import importlib
            return importlib.import_module(lib_name)
        except Exception:
            pass
    return None


@st.cache_resource(ttl=60)
def _open_desktop_session():
    """
    Try to open a desktop session via Workspace proxy (localhost:9000).
    Returns (module, True) if connected, (None, False) otherwise.
    Cached 60 s so the sidebar check doesn't hit the network every rerun.
    """
    lib = _import_lseg_lib()
    if lib is None:
        return None, False
    try:
        lib.open_session()          # Desktop session — no credentials needed
        sess = lib.session.get_default()
        if "Opened" in str(getattr(sess, "open_state", "")):
            return lib, True
    except Exception:
        pass
    return None, False


def lseg_desktop_available() -> bool:
    """True only when Refinitiv Workspace is running and the session is open."""
    _, ok = _open_desktop_session()
    return ok


# Backward-compat aliases used elsewhere in the app
def lseg_available() -> bool:
    return lseg_desktop_available()


def lseg_connected() -> bool:
    return lseg_desktop_available()


def refresh_lseg():
    """Force re-check of Workspace connection on next call."""
    _open_desktop_session.clear()


# ── Data fetching (only called when lseg_desktop_available() is True) ──────

def get_fundamentals_lseg(ticker: str) -> dict:
    """
    Fetch snapshot fundamentals from LSEG EDP via Workspace desktop session.
    Returns dict with keys: ebit, revenue, net_income, fcf, gross_profit,
    gross_margin, total_debt, cash, shares, ev_ebitda, eps_mean, price, pe_ratio
    Returns {} on any failure.
    """
    try:
        lib, ok = _open_desktop_session()
        if not ok or lib is None:
            return {}

        fields = [
            "TR.EBITActValue",
            "TR.TotalRevenue",
            "TR.NetIncome",
            "TR.FreeCashFlow",
            "TR.GrossProfit",
            "TR.GrossMargin",
            "TR.TotalDebt",
            "TR.CashAndSTInvestments",
            "TR.SharesOutstanding",
            "TR.EVToEBITDA",
            "TR.EPSMean",
            "TR.PriceClose",
        ]
        data = lib.get_data(universe=[ticker], fields=fields)
        if data is None or data.empty:
            return {}

        col_keys = [c for c in data.columns if c != "Instrument"]
        row = data.iloc[0]
        field_map = {
            "TR.EBITActValue":         "ebit",
            "TR.TotalRevenue":         "revenue",
            "TR.NetIncome":            "net_income",
            "TR.FreeCashFlow":         "fcf",
            "TR.GrossProfit":          "gross_profit",
            "TR.GrossMargin":          "gross_margin",
            "TR.TotalDebt":            "total_debt",
            "TR.CashAndSTInvestments": "cash",
            "TR.SharesOutstanding":    "shares",
            "TR.EVToEBITDA":           "ev_ebitda",
            "TR.EPSMean":              "eps_mean",
            "TR.PriceClose":           "price",
        }
        result = {}
        for i, field_code in enumerate(fields):
            if i >= len(col_keys):
                break
            key_name = field_map.get(field_code)
            if not key_name:
                continue
            v = row.get(col_keys[i])
            if v is not None and str(v) not in ("nan", "None", "<NA>", ""):
                try:
                    result[key_name] = float(v)
                except Exception:
                    pass

        if "price" in result and "eps_mean" in result and result["eps_mean"] > 0:
            result["pe_ratio"] = result["price"] / result["eps_mean"]

        return result
    except Exception:
        return {}


def get_historical_pe_lseg(ticker: str, years: int = 5) -> list:
    """
    Compute annual P/E from LSEG historical EPS + annual close prices.
    Returns list of floats (oldest→newest); [] on failure.
    """
    try:
        lib, ok = _open_desktop_session()
        if not ok or lib is None:
            return []

        eps_data = lib.get_data(
            universe=[ticker],
            fields=["TR.EPSActValue"],
            parameters={"SDate": f"-{years}Y", "EDate": "0D", "Frq": "FY"},
        )
        if eps_data is None or eps_data.empty:
            return []

        eps_col = [c for c in eps_data.columns if c != "Instrument"][0]
        eps_vals = [
            float(v) for v in eps_data[eps_col]
            if v is not None and str(v) not in ("nan", "None", "<NA>", "") and float(v) > 0
        ]
        if not eps_vals:
            return []

        price_data = lib.get_history(ticker, fields=["TRDPRC_1"], interval="1Y", count=years)
        if price_data is None or price_data.empty:
            return []

        price_col = price_data.columns[0]
        price_vals = [
            float(v) for v in price_data[price_col]
            if v is not None and str(v) not in ("nan", "None", "<NA>", "") and float(v) > 0
        ]
        if not price_vals:
            return []

        return [p / e for p, e in zip(price_vals, eps_vals) if e > 0 and 0 < p / e < 1000]
    except Exception:
        return []


def get_price_lseg(ticker: str) -> dict:
    """Real-time price from LSEG Workspace. Returns {} on failure."""
    try:
        lib, ok = _open_desktop_session()
        if not ok or lib is None:
            return {}

        data = lib.get_data(universe=[ticker], fields=["TR.PriceClose", "CF_CURRENCY"])
        if data is None or data.empty:
            return {}

        cols = [c for c in data.columns if c != "Instrument"]
        row   = data.iloc[0]
        price = row.get(cols[0]) if cols else None
        ccy   = row.get(cols[1]) if len(cols) > 1 else "USD"
        return {
            "price":    float(price) if price and str(price) not in ("nan", "None") else None,
            "currency": str(ccy) if ccy and str(ccy) not in ("nan", "None") else "USD",
            "source":   "lseg",
        }
    except Exception:
        return {}
