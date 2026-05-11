# core/engine.py — P&L calculation, compliance checks, portfolio analytics
import json
import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
from config import COMPLIANCE, TARGET_5X_USD, TARGET_10X_USD

# ── Build enriched portfolio DataFrame ───────────────────────────
def build_portfolio(holdings_df: pd.DataFrame,
                    prices: dict,
                    fx_rate: float,
                    report_ccy: str = "USD") -> pd.DataFrame:
    """
    Merges holdings with live prices, computes P&L, converts to report_ccy.
    Returns enriched DataFrame ready for display.
    """
    rows = []
    for _, h in holdings_df.iterrows():
        ticker = h["ticker"]
        ccy    = h["ccy"]
        shares = float(h["total_shares"])
        cost_l = float(h["avg_cost_local"])

        # Price
        price_info  = prices.get(ticker, {})
        live_price  = price_info.get("price")
        price_ts    = price_info.get("timestamp", "—")
        price_error = price_info.get("error")

        # Manual override for structured products
        manual = h.get("manual_price")
        if pd.notna(manual) and manual:
            live_price = float(manual)

        # Market values
        if live_price:
            mv_local = shares * live_price
            cost_total_local = shares * cost_l
            gl_local = mv_local - cost_total_local
            gl_pct   = (gl_local / cost_total_local * 100) if cost_total_local else 0
        else:
            mv_local = cost_total_local = gl_local = gl_pct = None

        # Convert to USD and HKD
        if ccy == "HKD":
            mv_usd  = mv_local / fx_rate  if mv_local  is not None else None
            cost_usd= cost_total_local / fx_rate if cost_total_local is not None else None
            gl_usd  = gl_local / fx_rate  if gl_local  is not None else None
            mv_hkd  = mv_local
        else:  # USD
            mv_usd  = mv_local
            cost_usd= cost_total_local
            gl_usd  = gl_local
            mv_hkd  = mv_local * fx_rate if mv_local is not None else None

        # Reporting currency
        mv_report   = mv_hkd  if report_ccy == "HKD" else mv_usd
        gl_report   = mv_hkd - cost_total_local * fx_rate if (report_ccy == "HKD" and mv_hkd and cost_total_local) else gl_usd

        # Broker breakdown
        try:
            brokers = json.loads(h.get("brokers_json", "[]"))
        except Exception:
            brokers = []
        broker_names = ", ".join({b["broker"] for b in brokers}) if brokers else "—"

        rows.append({
            "ticker":         ticker,
            "name":           h["name"],
            "region":         h["region"],
            "sector":         h["sector"],
            "barbell_class":  h["barbell_class"],
            "ccy":            ccy,
            "shares":         shares,
            "cost_local":     cost_l,
            "cost_total_local": cost_total_local,
            "live_price":     live_price,
            "price_ts":       price_ts,
            "price_error":    price_error,
            "mv_local":       mv_local,
            "mv_usd":         mv_usd,
            "mv_hkd":         mv_hkd,
            "mv_report":      mv_report,
            "cost_usd":       cost_usd,
            "gl_usd":         gl_usd,
            "gl_local":       gl_local,
            "gl_pct":         gl_pct,
            "gl_report":      gl_report,
            "brokers":        broker_names,
            "brokers_list":   brokers,
            "compliance_flag":h.get("compliance_flag", ""),
            "notes":          h.get("notes", ""),
        })

    df = pd.DataFrame(rows)
    return df


# ── Portfolio summary metrics ─────────────────────────────────────
def portfolio_summary(df: pd.DataFrame, report_ccy: str = "USD") -> dict:
    valid = df[df["mv_report"].notna()]
    total_mv   = valid["mv_report"].sum()
    total_cost = valid["cost_usd"].sum() if report_ccy == "USD" else (valid["cost_usd"] * 7.834).sum()
    total_gl   = valid["gl_report"].sum() if "gl_report" in valid else 0

    return {
        "total_mv":       total_mv,
        "total_cost":     total_cost,
        "total_gl":       total_gl,
        "total_gl_pct":   (total_gl / total_cost * 100) if total_cost else 0,
        "n_positions":    len(df),
        "target_5x":      TARGET_5X_USD,
        "target_10x":     TARGET_10X_USD,
        "pct_to_5x":      (total_mv / TARGET_5X_USD * 100) if TARGET_5X_USD else 0,
        "pct_to_10x":     (total_mv / TARGET_10X_USD * 100) if TARGET_10X_USD else 0,
        "report_ccy":     report_ccy,
    }


# ── Allocation breakdowns ─────────────────────────────────────────
def allocation_by(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Group by barbell_class / sector / region and sum MV."""
    valid = df[df["mv_usd"].notna()].copy()
    total = valid["mv_usd"].sum()
    grouped = (
        valid.groupby(group_col)["mv_usd"]
        .sum()
        .reset_index()
        .rename(columns={"mv_usd": "mv_usd"})
    )
    grouped["pct"] = grouped["mv_usd"] / total * 100
    grouped = grouped.sort_values("mv_usd", ascending=False)
    return grouped


# ── Concentration alerts ──────────────────────────────────────────
CONCENTRATION_THRESHOLD_PCT = 5.0   # flag if single position > 5% of portfolio

def concentration_alerts(df: pd.DataFrame) -> pd.DataFrame:
    valid = df[df["mv_usd"].notna()].copy()
    total = valid["mv_usd"].sum()
    valid["pct_of_port"] = valid["mv_usd"] / total * 100
    alerts = valid[valid["pct_of_port"] >= CONCENTRATION_THRESHOLD_PCT].copy()
    alerts = alerts.sort_values("pct_of_port", ascending=False)
    return alerts[["ticker", "name", "sector", "region",
                    "mv_usd", "pct_of_port", "brokers"]]


# ── Compliance checks ─────────────────────────────────────────────
def compliance_check(df: pd.DataFrame) -> pd.DataFrame:
    """Returns rows with compliance issues."""
    issues = []
    banned = [s.lower() for s in COMPLIANCE["banned_sectors"]]
    for _, row in df.iterrows():
        flags = []
        if any(b in row["sector"].lower() for b in banned):
            flags.append("BANNED_SECTOR")
        if row.get("compliance_flag"):
            flags.append(row["compliance_flag"])
        if flags:
            issues.append({**row, "flags": ", ".join(flags)})
    return pd.DataFrame(issues)


# ── Weighted average cost basis calculator ────────────────────────
def calc_new_avg_cost(current_shares: float, current_avg: float,
                      new_shares: float, new_price: float) -> float:
    """Returns new weighted average cost after a BUY."""
    total = current_shares + new_shares
    if total == 0:
        return 0
    return (current_shares * current_avg + new_shares * new_price) / total


# ── Progress to target ────────────────────────────────────────────
def target_progress(total_mv_usd: float) -> dict:
    years_to_2035 = 2035 - 2026
    cagr_needed_5x = (TARGET_5X_USD / total_mv_usd) ** (1 / years_to_2035) - 1 if total_mv_usd else 0
    return {
        "current_usd":    total_mv_usd,
        "target_5x":      TARGET_5X_USD,
        "target_10x":     TARGET_10X_USD,
        "gap_5x":         TARGET_5X_USD  - total_mv_usd,
        "gap_10x":        TARGET_10X_USD - total_mv_usd,
        "pct_to_5x":      total_mv_usd / TARGET_5X_USD  * 100,
        "pct_to_10x":     total_mv_usd / TARGET_10X_USD * 100,
        "cagr_needed_5x": cagr_needed_5x * 100,
        "multiplier_now": total_mv_usd / (total_mv_usd / 1) if total_mv_usd else 1,
    }


# ── Stock Analyzer — 10-pillar fundamental framework ─────────────
@st.cache_data(ttl=3600)
def calculate_pillars(ticker_sym: str) -> dict:
    """
    Fetches yfinance data and evaluates any ticker across 10 fundamental pillars.
    Returns: {error, company_info, pillars, score, verdict, historical}
    pillars is a list of 10 dicts: {number, name, value, rating, note}
    rating is one of: GREEN, YELLOW, RED, NA
    """
    ticker_sym = ticker_sym.strip().upper()

    def _err(msg):
        return {"error": msg, "company_info": {}, "pillars": [], "score": 0,
                "verdict": "N/A", "historical": []}

    try:
        tk   = yf.Ticker(ticker_sym)
        info = tk.info or {}
    except Exception as e:
        return _err(f"Could not fetch '{ticker_sym}': {e}")

    price_check = (info.get("currentPrice") or info.get("regularMarketPrice")
                   or info.get("previousClose"))
    if not price_check:
        return _err(f"Ticker '{ticker_sym}' not found or has no price data.")

    # ── Company info ─────────────────────────────────────────────
    company_info = {
        "name":         info.get("longName") or info.get("shortName") or ticker_sym,
        "sector":       info.get("sector") or info.get("quoteType", "N/A"),
        "market_cap":   info.get("marketCap"),
        "price":        float(price_check),
        "currency":     info.get("currency", "USD"),
        "week_52_high": info.get("fiftyTwoWeekHigh"),
        "week_52_low":  info.get("fiftyTwoWeekLow"),
    }

    # ── Financial statements ─────────────────────────────────────
    def _stmt(attr):
        try:
            df = getattr(tk, attr)
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    inc = _stmt("income_stmt")
    bal = _stmt("balance_sheet")
    cf  = _stmt("cash_flow")

    def _v(df, keys, col=0):
        if df.empty or col >= len(df.columns):
            return None
        for k in ([keys] if isinstance(keys, str) else keys):
            try:
                if k in df.index:
                    v = df.loc[k].iloc[col]
                    if pd.notna(v) and v != 0:
                        return float(v)
            except Exception:
                pass
        return None

    def _col(df, keys, n=4):
        return [_v(df, keys, i) for i in range(min(n, max(1, len(df.columns))))]

    def _cagr(start, end, yrs):
        if start and end and start > 0 and end > 0 and yrs > 0:
            return (end / start) ** (1 / yrs) - 1
        return None

    pillars = []

    # ── Pillar 1: P/E TTM vs 5yr avg ────────────────────────────
    current_pe = info.get("trailingPE")
    avg_pe_5y  = None
    try:
        hist_5y = tk.history(period="5y", interval="3mo")
        if not hist_5y.empty and not inc.empty:
            shares_out = (info.get("sharesOutstanding")
                          or info.get("impliedSharesOutstanding"))
            if shares_out and shares_out > 0:
                pe_list = []
                for i, col_date in enumerate(inc.columns[:5]):
                    ni = _v(inc, ["Net Income", "Net Income Common Stockholders",
                                   "Net Income Including Noncontrolling Interests"], i)
                    if ni and ni > 0:
                        eps = ni / shares_out
                        start_dt = col_date - pd.DateOffset(months=12)
                        mask = (hist_5y.index >= start_dt) & (hist_5y.index <= col_date)
                        price_slice = hist_5y.loc[mask, "Close"]
                        if not price_slice.empty and eps > 0:
                            pe_yr = float(price_slice.mean()) / eps
                            if 0 < pe_yr < 1000:
                                pe_list.append(pe_yr)
                if pe_list:
                    avg_pe_5y = sum(pe_list) / len(pe_list)
    except Exception:
        pass

    if current_pe and avg_pe_5y:
        diff = (current_pe - avg_pe_5y) / avg_pe_5y * 100
        if current_pe < avg_pe_5y:
            rating, note = "GREEN", f"Below 5yr avg by {abs(diff):.0f}%"
        elif diff <= 10:
            rating, note = "YELLOW", "Within 10% of 5yr avg"
        else:
            rating, note = "RED",   f"Above 5yr avg by {diff:.0f}%"
        val = f"{current_pe:.1f}x (5yr avg: {avg_pe_5y:.1f}x)"
    elif current_pe:
        rating, val, note = "NA", f"{current_pe:.1f}x (5yr avg: N/A)", "5yr avg unavailable"
    else:
        rating, val, note = "NA", "N/A", "P/E data unavailable"
    pillars.append({"number": 1, "name": "P/E vs 5yr Avg", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 2: ROIC ───────────────────────────────────────────
    ebit = _v(inc, ["EBIT", "Operating Income", "Total Operating Income As Reported"])
    tax  = _v(inc, ["Tax Provision", "Income Tax Expense"])
    pret = _v(inc, ["Pretax Income", "Income Before Tax"])
    eq   = _v(bal, ["Stockholders Equity", "Common Stockholders Equity",
                     "Total Equity Gross Minority Interest"])
    debt = _v(bal, ["Total Debt", "Long Term Debt And Capital Lease Obligation",
                     "Long Term Debt"])
    cash = _v(bal, ["Cash And Cash Equivalents",
                     "Cash Cash Equivalents And Short Term Investments"])
    if ebit and eq is not None:
        tr  = abs(tax / pret) if (tax and pret and pret != 0) else 0.21
        tr  = min(max(tr, 0), 0.5)
        ic  = (eq or 0) + (debt or 0) - (cash or 0)
        if ic > 0:
            roic = ebit * (1 - tr) / ic * 100
            if roic > 15:
                rating, note = "GREEN", "Strong capital returns"
            elif roic >= 10:
                rating, note = "YELLOW", "Adequate capital returns"
            else:
                rating, note = "RED",   "Weak capital returns"
            val = f"{roic:.1f}%"
        else:
            rating, val, note = "NA", "N/A", "Negative invested capital"
    else:
        rating, val, note = "NA", "N/A", "Insufficient financial data"
    pillars.append({"number": 2, "name": "ROIC", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 3: Revenue Growth 3yr CAGR ────────────────────────
    revs = _col(inc, ["Total Revenue", "Revenue"], 4)
    valid_r = [(i, v) for i, v in enumerate(revs) if v and v > 0]
    cagr_rev = _cagr(valid_r[-1][1], valid_r[0][1], valid_r[-1][0]) if len(valid_r) >= 2 else None
    if cagr_rev is not None:
        pct = cagr_rev * 100
        rating = "GREEN" if pct > 10 else ("YELLOW" if pct >= 5 else "RED")
        val, note = f"{pct:.1f}% CAGR", "Revenue CAGR"
    else:
        rating, val, note = "NA", "N/A", "Insufficient revenue data"
    pillars.append({"number": 3, "name": "Revenue Growth 3yr", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 4: Net Income Growth 3yr CAGR ─────────────────────
    nis = _col(inc, ["Net Income", "Net Income Common Stockholders",
                      "Net Income Including Noncontrolling Interests"], 4)
    valid_ni = [(i, v) for i, v in enumerate(nis) if v and v > 0]
    cagr_ni = _cagr(valid_ni[-1][1], valid_ni[0][1], valid_ni[-1][0]) if len(valid_ni) >= 2 else None
    if cagr_ni is not None:
        pct = cagr_ni * 100
        rating = "GREEN" if pct > 10 else ("YELLOW" if pct >= 5 else "RED")
        val, note = f"{pct:.1f}% CAGR", "Net income CAGR"
    else:
        rating, val, note = "NA", "N/A", "Insufficient net income data"
    pillars.append({"number": 4, "name": "Net Income Growth 3yr", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 5: Shares Outstanding 5yr change ──────────────────
    shs = _col(inc, ["Diluted Average Shares", "Basic Average Shares",
                      "Ordinary Shares Number"], 5)
    valid_sh = [(i, v) for i, v in enumerate(shs) if v and v > 0]
    if len(valid_sh) >= 2:
        sh_new, sh_old = valid_sh[0][1], valid_sh[-1][1]
        chg = (sh_new - sh_old) / sh_old * 100
        if chg < -0.5:
            rating, note = "GREEN", f"Buybacks: {abs(chg):.1f}% reduction"
        elif abs(chg) <= 2:
            rating, note = "YELLOW", f"Flat ({chg:+.1f}%)"
        else:
            rating, note = "RED",   f"Dilution: +{chg:.1f}%"
        val = f"{chg:+.1f}% ({len(valid_sh)-1}yr)"
    else:
        rating, val, note = "NA", "N/A", "Share count data unavailable"
    pillars.append({"number": 5, "name": "Shares Outstanding 5yr", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 6: Net Debt / EBITDA ──────────────────────────────
    ebitda = info.get("ebitda")
    if not ebitda:
        op = _v(inc, ["Operating Income", "EBIT", "Total Operating Income As Reported"])
        da = _v(cf,  ["Depreciation Amortization Depletion",
                       "Depreciation And Amortization", "Depreciation"])
        if op and da:
            ebitda = op + abs(da)
    td = _v(bal, ["Total Debt", "Long Term Debt And Capital Lease Obligation"])
    if td is None:
        td = ((_v(bal, ["Long Term Debt"]) or 0) +
              (_v(bal, ["Current Debt And Capital Lease Obligation",
                         "Short Term Debt"]) or 0))
    csh = (_v(bal, ["Cash And Cash Equivalents",
                     "Cash Cash Equivalents And Short Term Investments"])
           or info.get("totalCash") or 0)
    if ebitda and abs(ebitda) > 0:
        nd_eb = ((td or 0) - (csh or 0)) / abs(ebitda)
        if nd_eb < 2:
            rating, note = "GREEN",  "Low leverage"
        elif nd_eb <= 4:
            rating, note = "YELLOW", "Moderate leverage"
        else:
            rating, note = "RED",    "High leverage"
        val = f"{nd_eb:.1f}x"
    else:
        rating, val, note = "NA", "N/A", "EBITDA data unavailable"
    pillars.append({"number": 6, "name": "Net Debt / EBITDA", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 7: FCF Growth 3yr CAGR ────────────────────────────
    fcfs = _col(cf, ["Free Cash Flow"], 4)
    if not any(v for v in fcfs if v):
        ocfs  = _col(cf, ["Operating Cash Flow",
                           "Cash Flow From Continuing Operating Activities"], 4)
        capes = _col(cf, ["Capital Expenditure", "Purchase Of PPE"], 4)
        fcfs  = [(o + c) if (o is not None and c is not None) else o
                 for o, c in zip(ocfs, capes)]
    valid_fcf = [(i, v) for i, v in enumerate(fcfs) if v and v > 0]
    cagr_fcf = (_cagr(valid_fcf[-1][1], valid_fcf[0][1], valid_fcf[-1][0])
                if len(valid_fcf) >= 2 else None)
    if cagr_fcf is not None:
        pct = cagr_fcf * 100
        rating = "GREEN" if pct > 10 else ("YELLOW" if pct >= 5 else "RED")
        val, note = f"{pct:.1f}% CAGR", "FCF CAGR"
    else:
        rating, val, note = "NA", "N/A", "Insufficient FCF data"
    pillars.append({"number": 7, "name": "FCF Growth 3yr", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 8: Price / FCF ────────────────────────────────────
    mkt_cap  = info.get("marketCap")
    fcf_last = fcfs[0] if fcfs else None
    if mkt_cap and fcf_last and fcf_last > 0:
        p_fcf = mkt_cap / fcf_last
        if p_fcf < 20:
            rating, note = "GREEN",  "Cheap on P/FCF"
        elif p_fcf <= 30:
            rating, note = "YELLOW", "Fair on P/FCF"
        else:
            rating, note = "RED",    "Expensive on P/FCF"
        val = f"{p_fcf:.1f}x"
    else:
        rating, val, note = "NA", "N/A", "FCF or market cap unavailable"
    pillars.append({"number": 8, "name": "Price / FCF", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 9: Gross Margin Trend 3yr ─────────────────────────
    gps   = _col(inc, ["Gross Profit"], 4)
    revs9 = _col(inc, ["Total Revenue", "Revenue"], 4)
    margins = [(gp / rv * 100) if (gp is not None and rv and rv > 0) else None
               for gp, rv in zip(gps, revs9)]
    valid_m = [(i, m) for i, m in enumerate(margins) if m is not None]
    if len(valid_m) >= 2:
        m_new, m_old = valid_m[0][1], valid_m[-1][1]
        chg = m_new - m_old
        if chg > 2:
            rating, note = "GREEN",  f"Expanding ({chg:+.1f}pp)"
        elif chg >= -2:
            rating, note = "YELLOW", f"Stable ({chg:+.1f}pp)"
        else:
            rating, note = "RED",    f"Declining ({chg:+.1f}pp)"
        val = f"{m_new:.1f}% (was {m_old:.1f}%)"
    else:
        rating, val, note = "NA", "N/A", "Insufficient gross margin data"
    pillars.append({"number": 9, "name": "Gross Margin Trend 3yr", "value": val,
                    "rating": rating, "note": note})

    # ── Pillar 10: Total Return vs Benchmark 3yr ─────────────────
    benchmark = "^HSI" if ticker_sym.endswith(".HK") else "SPY"
    try:
        h_stock = tk.history(period="3y", auto_adjust=True)
        h_bench = yf.Ticker(benchmark).history(period="3y", auto_adjust=True)
        if not h_stock.empty and not h_bench.empty:
            r_s = (h_stock["Close"].iloc[-1] / h_stock["Close"].iloc[0] - 1) * 100
            r_b = (h_bench["Close"].iloc[-1] / h_bench["Close"].iloc[0] - 1) * 100
            exc = r_s - r_b
            if exc > 5:
                rating, note = "GREEN",  f"Beats {benchmark} by {exc:.1f}%"
            elif exc >= -5:
                rating, note = "YELLOW", f"Within 5% of {benchmark}"
            else:
                rating, note = "RED",    f"Trails {benchmark} by {abs(exc):.1f}%"
            val = f"Stock {r_s:+.1f}% vs {benchmark} {r_b:+.1f}%"
        else:
            rating, val, note = "NA", "N/A", "Price history unavailable"
    except Exception as ex:
        rating, val, note = "NA", "N/A", f"Error: {str(ex)[:40]}"
    pillars.append({"number": 10, "name": f"vs {benchmark} 3yr Return", "value": val,
                    "rating": rating, "note": note})

    # ── Score & Verdict ───────────────────────────────────────────
    score   = sum(1 for p in pillars if p["rating"] == "GREEN")
    verdict = "CHEAP" if score >= 8 else ("FAIR" if score >= 5 else "EXPENSIVE")

    # ── Historical table for PDF ──────────────────────────────────
    historical = []
    if not inc.empty:
        for i, col_date in enumerate(inc.columns[:5]):
            try:
                year = col_date.year
            except Exception:
                year = str(col_date)[:4]
            rv  = _v(inc, ["Total Revenue", "Revenue"], i)
            ni  = _v(inc, ["Net Income", "Net Income Common Stockholders"], i)
            gp  = _v(inc, ["Gross Profit"], i)
            sh  = _v(inc, ["Diluted Average Shares", "Basic Average Shares"], i)
            fcf_h = fcfs[i] if i < len(fcfs) else None
            gm  = (gp / rv * 100) if (gp is not None and rv and rv > 0) else None
            historical.append({"year": year, "revenue": rv, "net_income": ni,
                                "fcf": fcf_h, "gross_margin_pct": gm, "shares": sh})

    return {
        "error":        None,
        "company_info": company_info,
        "pillars":      pillars,
        "score":        score,
        "verdict":      verdict,
        "historical":   historical,
    }
