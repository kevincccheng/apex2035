# core/lseg_data.py — LSEG EDP data integration (supplements yfinance)
# Requires Refinitiv Workspace desktop app running locally (localhost:9000).
# Falls back to yfinance gracefully when Workspace is closed.

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
    """True if EDP_API_KEY is configured (key present, doesn't test connectivity)."""
    return bool(get_edp_key())


@st.cache_resource(ttl=120)
def _get_lseg_module():
    """
    Import and open an LSEG session once per process.
    Returns (module, True) only when the session is actually Opened.
    Requires Refinitiv Workspace / Eikon desktop app to be running.
    """
    key = get_edp_key()
    if not key:
        return None, False

    for _lib in ("lseg.data", "refinitiv.data"):
        try:
            import importlib
            ld = importlib.import_module(_lib)
            ld.open_session(app_key=key)
            # Verify the session is actually open (not just attempted)
            sess = ld.session.get_default()
            state = str(getattr(sess, "open_state", ""))
            if "Opened" not in state:
                continue
            return ld, True
        except Exception:
            continue

    return None, False


def lseg_connected() -> bool:
    """True only when the LSEG session is open and Workspace is running."""
    _, ok = _get_lseg_module()
    return ok


def refresh_lseg():
    """Force re-check of LSEG connection on next call (use after opening Workspace)."""
    _get_lseg_module.clear()


def _extract(data, col_name: str):
    """Safely extract a float from a get_data result column."""
    try:
        # Column headers from get_data are verbose names, not field codes.
        # Search by substring match against known verbose names.
        matching = [c for c in data.columns if c != "Instrument"]
        # Try exact match first, then first non-instrument column
        val = data.iloc[0].get(col_name)
        if val is None:
            return None
        s = str(val)
        if s in ("nan", "None", "<NA>", ""):
            return None
        return float(val)
    except Exception:
        return None


def get_fundamentals_lseg(ticker: str) -> dict:
    """
    Fetch snapshot fundamentals from LSEG EDP using confirmed working fields.
    Returns dict with standardised keys; returns {} on any failure.

    Confirmed working fields (tested 2026-05-11):
      TR.EBITActValue, TR.TotalRevenue, TR.NetIncome, TR.FreeCashFlow,
      TR.GrossProfit, TR.GrossMargin, TR.TotalDebt, TR.CashAndSTInvestments,
      TR.SharesOutstanding, TR.EVToEBITDA, TR.EPSMean, TR.PriceClose
    """
    try:
        rd, ok = _get_lseg_module()
        if not ok or rd is None:
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
        data = rd.get_data(universe=[ticker], fields=fields)
        if data is None or data.empty:
            return {}

        row = data.iloc[0]
        result = {}

        def _v(col_substr):
            for col in data.columns:
                if col == "Instrument":
                    continue
                v = row.get(col)
                if v is None or str(v) in ("nan", "None", "<NA>", ""):
                    continue
                try:
                    return float(v)
                except Exception:
                    pass
            return None

        # Map each field by iterating get_data result columns in order
        col_keys = [c for c in data.columns if c != "Instrument"]
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
        # get_data returns columns in the same order as fields requested
        for i, field_code in enumerate(fields):
            if i >= len(col_keys):
                break
            col = col_keys[i]
            key_name = field_map.get(field_code)
            if not key_name:
                continue
            v = row.get(col)
            if v is not None and str(v) not in ("nan", "None", "<NA>", ""):
                try:
                    result[key_name] = float(v)
                except Exception:
                    pass

        # Derived: P/E from price / eps_mean
        if "price" in result and "eps_mean" in result and result["eps_mean"] > 0:
            result["pe_ratio"] = result["price"] / result["eps_mean"]

        return result

    except Exception:
        return {}


def get_historical_fundamentals_lseg(ticker: str, years: int = 5) -> list:
    """
    Fetch annual fundamental data for past N fiscal years.
    Returns list of dicts (most recent first): {year, revenue, net_income, fcf,
    gross_profit, eps}. Returns [] on failure.
    """
    try:
        rd, ok = _get_lseg_module()
        if not ok or rd is None:
            return []

        fields = [
            "TR.TotalRevenue",
            "TR.NetIncome",
            "TR.FreeCashFlow",
            "TR.GrossProfit",
            "TR.EPSActValue",
        ]
        data = rd.get_data(
            universe=[ticker],
            fields=fields,
            parameters={"SDate": f"-{years}Y", "EDate": "0D", "Frq": "FY"},
        )
        if data is None or data.empty:
            return []

        col_keys = [c for c in data.columns if c != "Instrument"]
        rows = []
        for i, (_, row_data) in enumerate(data.iterrows()):
            entry = {"year": years - i}
            for j, field_code in enumerate(fields):
                if j >= len(col_keys):
                    break
                v = row_data.iloc[j + 1]  # +1 to skip Instrument
                if v is not None and str(v) not in ("nan", "None", "<NA>", ""):
                    try:
                        key_map = {
                            "TR.TotalRevenue": "revenue",
                            "TR.NetIncome":    "net_income",
                            "TR.FreeCashFlow": "fcf",
                            "TR.GrossProfit":  "gross_profit",
                            "TR.EPSActValue":  "eps",
                        }
                        entry[key_map[field_code]] = float(v)
                    except Exception:
                        pass
            rows.append(entry)
        return rows

    except Exception:
        return []


def get_historical_pe_lseg(ticker: str, years: int = 5) -> list:
    """
    Compute annual P/E ratios using LSEG historical EPS + annual close prices.
    Returns list of P/E floats (oldest→newest); [] on failure.
    """
    try:
        rd, ok = _get_lseg_module()
        if not ok or rd is None:
            return []

        # Annual EPS history
        eps_data = rd.get_data(
            universe=[ticker],
            fields=["TR.EPSActValue"],
            parameters={"SDate": f"-{years}Y", "EDate": "0D", "Frq": "FY"},
        )
        if eps_data is None or eps_data.empty:
            return []

        eps_col = [c for c in eps_data.columns if c != "Instrument"][0]
        eps_vals = [float(v) for v in eps_data[eps_col]
                    if v is not None and str(v) not in ("nan", "None", "<NA>", "")
                    and float(v) > 0]
        if not eps_vals:
            return []

        # Annual close prices (TRDPRC_1 works with get_history; TR.PriceClose does not)
        price_data = rd.get_history(
            ticker,
            fields=["TRDPRC_1"],
            interval="1Y",
            count=years,
        )
        if price_data is None or price_data.empty:
            return []

        price_col = price_data.columns[0]
        price_vals = [float(v) for v in price_data[price_col]
                      if v is not None and str(v) not in ("nan", "None", "<NA>", "")
                      and float(v) > 0]
        if not price_vals:
            return []

        pe_list = []
        for p, e in zip(price_vals, eps_vals):
            if e > 0:
                pe = p / e
                if 0 < pe < 1000:
                    pe_list.append(pe)
        return pe_list

    except Exception:
        return []


def get_price_lseg(ticker: str) -> dict:
    """Real-time price from LSEG EDP. Returns {} on failure."""
    try:
        rd, ok = _get_lseg_module()
        if not ok or rd is None:
            return {}

        data = rd.get_data(universe=[ticker], fields=["TR.PriceClose", "CF_CURRENCY"])
        if data is None or data.empty:
            return {}

        row = data.iloc[0]
        cols = [c for c in data.columns if c != "Instrument"]
        price = row.get(cols[0]) if cols else None
        ccy   = row.get(cols[1]) if len(cols) > 1 else "USD"
        return {
            "price":    float(price) if price and str(price) not in ("nan", "None") else None,
            "currency": str(ccy) if ccy and str(ccy) not in ("nan", "None") else "USD",
            "source":   "lseg",
        }
    except Exception:
        return {}
