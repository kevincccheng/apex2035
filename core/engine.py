# core/engine.py — P&L calculation, compliance checks, portfolio analytics
import json
import pandas as pd
import numpy as np
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
