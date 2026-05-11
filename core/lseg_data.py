# core/lseg_data.py — Optional LSEG EDP data integration
# Supplements yfinance with richer fundamentals (especially HK stocks).
# Requires LSEG Workspace / Eikon desktop app running locally, OR
# valid EDP platform credentials in EDP_API_KEY.
# Falls back to yfinance gracefully when unavailable.

import os
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_edp_key() -> str | None:
    key = os.getenv("EDP_API_KEY")
    if not key:
        try:
            key = st.secrets.get("EDP_API_KEY")
        except Exception:
            pass
    return key or None


def lseg_available() -> bool:
    return bool(get_edp_key())


@st.cache_resource
def _get_lseg_module():
    """
    Import and open an LSEG session once per process.
    Returns (module, True) when connected, (None, False) otherwise.
    Tries lseg.data (lseg-data package) then refinitiv.data as fallback.
    """
    key = get_edp_key()
    if not key:
        return None, False

    # Try lseg.data (pip install lseg-data)
    try:
        import lseg.data as ld
        ld.open_session(app_key=key)
        return ld, True
    except Exception:
        pass

    # Fallback: refinitiv.data (pip install refinitiv-data)
    try:
        import refinitiv.data as rd
        rd.open_session(app_key=key)
        return rd, True
    except Exception:
        pass

    return None, False


def get_fundamentals_lseg(ticker: str) -> dict:
    """
    Fetch snapshot fundamentals from LSEG EDP.
    Returns dict with standardised keys; returns {} on any failure.
    Keys: pe_ratio, roic, revenue, net_income, fcf,
          gross_margin, shares, ev_ebitda, p_bv
    """
    try:
        rd, ok = _get_lseg_module()
        if not ok or rd is None:
            return {}

        fields = [
            "TR.PERatio",
            "TR.ROIC",
            "TR.RevenueActValue",
            "TR.NetIncomeActValue",
            "TR.FreeCashFlow",
            "TR.GrossMargin",
            "TR.TotalSharesOutstanding",
            "TR.EVToEBITDA",
            "TR.PriceToBVPerShare",
        ]
        data = rd.get_data(universe=[ticker], fields=fields)
        if data is None or data.empty:
            return {}

        row = data.iloc[0]
        mapping = {
            "TR.PERatio":                "pe_ratio",
            "TR.ROIC":                   "roic",
            "TR.RevenueActValue":        "revenue",
            "TR.NetIncomeActValue":      "net_income",
            "TR.FreeCashFlow":           "fcf",
            "TR.GrossMargin":            "gross_margin",
            "TR.TotalSharesOutstanding": "shares",
            "TR.EVToEBITDA":             "ev_ebitda",
            "TR.PriceToBVPerShare":      "p_bv",
        }
        result = {}
        for col, key in mapping.items():
            if col in data.columns:
                v = row.get(col)
                if v is not None and str(v) not in ("nan", "None", ""):
                    try:
                        result[key] = float(v)
                    except Exception:
                        pass
        return result

    except Exception:
        return {}


def get_historical_pe_lseg(ticker: str, years: int = 5) -> list:
    """
    Fetch annual P/E ratios for past N fiscal years from LSEG.
    Returns list of floats (most recent first); [] on failure.
    """
    try:
        rd, ok = _get_lseg_module()
        if not ok or rd is None:
            return []

        data = rd.get_data(
            universe=[ticker],
            fields=["TR.PERatio"],
            parameters={"SDate": f"-{years}Y", "EDate": "0D", "Frq": "FY"},
        )
        if data is None or data.empty:
            return []

        pe_list = []
        for val in data["TR.PERatio"]:
            if val is not None and str(val) not in ("nan", "None", ""):
                try:
                    pe_list.append(float(val))
                except Exception:
                    pass
        return pe_list

    except Exception:
        return []


def get_price_lseg(ticker: str) -> dict:
    """Real-time price from LSEG EDP. Returns {} on failure."""
    try:
        rd, ok = _get_lseg_module()
        if not ok or rd is None:
            return {}

        data = rd.get_data(
            universe=[ticker],
            fields=["TR.PriceClose", "TR.Currency"],
        )
        if data is None or data.empty:
            return {}

        row = data.iloc[0]
        price = row.get("TR.PriceClose")
        return {
            "price":    float(price) if price else None,
            "currency": row.get("TR.Currency", "USD"),
            "source":   "lseg",
        }
    except Exception:
        return {}
