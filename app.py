# app.py — Project Apex 2035 | Portfolio Dashboard
# Run: streamlit run app.py

import json
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import (
    PROJECT_NAME, TARGET_5X_USD, TARGET_10X_USD,
    BROKERS, ACTIVE_BROKERS, LEGACY_BROKERS,
    REPORT_CURRENCIES, DEFAULT_CURRENCY,
)
from core.prices import get_prices_batch, get_hkd_usd_rate
from core.engine import (
    build_portfolio, portfolio_summary, allocation_by,
    concentration_alerts, compliance_check,
    calc_new_avg_cost, target_progress,
)

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Apex 2035",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Password gate ─────────────────────────────────────────────────
def check_password():
    correct = st.secrets.get("app_password", "CHANGE_ME")
    if st.session_state.get("authenticated"):
        return True
    st.title("📈 Apex 2035")
    st.caption("Private portfolio dashboard — authorised access only.")
    pwd = st.text_input("Password", type="password", key="pwd_input")
    if st.button("Enter", type="primary"):
        if pwd.strip() == correct.strip():
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error(f"Incorrect. App expects a {len(correct)}-character password. You entered {len(pwd.strip())} characters.")
    return False

if not check_password():
    st.stop()

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .metric-card {
        background: #1a1a2e; border-radius: 8px;
        padding: 14px 18px; margin-bottom: 8px;
    }
    .pos { color: #4ade80; font-weight: 600; }
    .neg { color: #f87171; font-weight: 600; }
    .neu { color: #94a3b8; }
    .target-bar { background: #0f172a; border-radius: 6px;
                  padding: 10px 14px; margin: 4px 0; }
    div[data-testid="stTabs"] button { font-size: 14px; font-weight: 500; }
    .stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Determine if Google Sheets is configured ───────────────────────
SHEETS_AVAILABLE = "gcp_service_account" in st.secrets

if SHEETS_AVAILABLE:
    from core.sheets import read_holdings, append_trades, read_trades
else:
    # Offline mode: load from config.py directly (no Google Sheets needed for demo)
    from config import INITIAL_POSITIONS, HKD_USD_RATE
    import core.engine as engine

    def _build_offline_holdings() -> pd.DataFrame:
        rows = []
        for pos in INITIAL_POSITIONS:
            brokers = pos.get("brokers", [])
            total_shares = sum(b["shares"] for b in brokers)
            total_cost_w = sum(b["shares"] * b["avg_cost_local"] for b in brokers)
            avg_cost_l   = total_cost_w / total_shares if total_shares else 0
            avg_cost_usd = avg_cost_l / HKD_USD_RATE if pos["ccy"] == "HKD" else avg_cost_l
            rows.append({
                "ticker": pos["ticker"], "name": pos["name"],
                "region": pos["region"], "sector": pos["sector"],
                "barbell_class": pos["barbell_class"], "ccy": pos["ccy"],
                "total_shares": total_shares,
                "avg_cost_local": avg_cost_l, "avg_cost_usd": avg_cost_usd,
                "brokers_json": json.dumps(pos.get("brokers", [])),
                "manual_price": None, "compliance_flag": "",
                "lockup_expiry": "", "notes": "", "last_updated": "",
            })
        return pd.DataFrame(rows)

    def read_holdings():
        return _build_offline_holdings()

    def append_trades(trades, source="manual"):
        st.warning("Google Sheets not configured — trades not persisted. See SETUP.md.")


# ─────────────────────────────────────────────────────────────────
# SIDEBAR — global controls
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Controls")
    report_ccy = st.radio("Report currency", REPORT_CURRENCIES,
                           index=REPORT_CURRENCIES.index(DEFAULT_CURRENCY),
                           horizontal=True)
    ccy_sym = "HK$" if report_ccy == "HKD" else "$"

    st.divider()
    if st.button("🔄 Refresh prices"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"Project Apex 2035\nTarget: {ccy_sym}{TARGET_5X_USD:,.0f}\nHK tax: 0% CGT ✓")

    if not SHEETS_AVAILABLE:
        st.warning("⚠️ Offline mode\nGoogle Sheets not connected.\nSee SETUP.md to connect.")


# ─────────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data(report_ccy: str):
    holdings_df = read_holdings()
    tickers = tuple(holdings_df["ticker"].tolist())
    prices  = get_prices_batch(tickers)
    fx_rate = get_hkd_usd_rate()
    port_df = build_portfolio(holdings_df, prices, fx_rate, report_ccy)
    summary = portfolio_summary(port_df, report_ccy)
    progress = target_progress(summary["total_mv"] if report_ccy == "USD"
                               else summary["total_mv"] / fx_rate)
    return port_df, summary, progress, fx_rate


with st.spinner("Loading portfolio…"):
    port_df, summary, progress, fx_rate = load_data(report_ccy)

total_mv   = summary["total_mv"]
total_gl   = summary["total_gl"]
total_cost = summary["total_cost"]


# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
col_title, col_ts = st.columns([3, 1])
with col_title:
    st.title(f"📈 {PROJECT_NAME}")
with col_ts:
    st.caption(f"FX: USD/HKD = {fx_rate:.4f}\nPrices ~15 min delayed")

# Top KPI row
k1, k2, k3, k4, k5, k6 = st.columns(6)
gl_color = "normal" if total_gl >= 0 else "inverse"
k1.metric("Total Portfolio",
          f"{ccy_sym}{total_mv/1e6:.3f}M",
          f"{ccy_sym}{total_gl/1e6:+.3f}M")
k2.metric("Unrealized G/L",
          f"{ccy_sym}{total_gl:,.0f}",
          f"{total_gl/total_cost*100:+.1f}%" if total_cost else "—")
k3.metric("Positions", summary["n_positions"])
k4.metric("5x Target",
          f"{ccy_sym}{TARGET_5X_USD/1e6:.2f}M",
          f"{progress['pct_to_5x']:.1f}% there")
k5.metric("CAGR needed → 5x",
          f"{progress['cagr_needed_5x']:.1f}%",
          "by 2035")
k6.metric("Price source", "yfinance", "~15 min delay")

st.divider()

# ─────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Master Ledger",
    "🏦 Broker Recon",
    "🎯 Analytics",
    "⚠️ Alerts",
    "✏️ Trade Entry",
    "📄 Export",
])


# ══════════════════════════════════════════════════════════════════
# TAB 1 — MASTER LEDGER
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Consolidated Holdings — Master Ledger")

    # Filter controls
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        region_filter = st.multiselect("Region",
            sorted(port_df["region"].unique()), default=[])
    with fc2:
        sector_filter = st.multiselect("Sector",
            sorted(port_df["sector"].unique()), default=[])
    with fc3:
        barbell_filter = st.multiselect("Barbell",
            ["CORE", "TACTICAL", "SPECULATIVE"], default=[])
    with fc4:
        search = st.text_input("Search ticker / name", "")

    df_view = port_df.copy()
    if region_filter:  df_view = df_view[df_view["region"].isin(region_filter)]
    if sector_filter:  df_view = df_view[df_view["sector"].isin(sector_filter)]
    if barbell_filter: df_view = df_view[df_view["barbell_class"].isin(barbell_filter)]
    if search:
        s = search.lower()
        df_view = df_view[
            df_view["ticker"].str.lower().str.contains(s) |
            df_view["name"].str.lower().str.contains(s)
        ]

    df_view = df_view.sort_values("mv_usd", ascending=False, na_position="last")

    # Build display dataframe
    def fmt_price(row):
        if row["live_price"] is None:
            return "—"
        sym = "HK$" if row["ccy"] == "HKD" else "$"
        return f"{sym}{row['live_price']:,.2f}"

    def fmt_mv(val):
        if pd.isna(val): return "—"
        return f"{ccy_sym}{val:,.0f}"

    def fmt_gl(val, pct):
        if pd.isna(val): return "—"
        sign = "+" if val >= 0 else ""
        return f"{sign}{ccy_sym}{val:,.0f} ({sign}{pct:.1f}%)" if pd.notna(pct) else f"{sign}{ccy_sym}{val:,.0f}"

    display = pd.DataFrame({
        "Ticker":       df_view["ticker"],
        "Name":         df_view["name"],
        "Region":       df_view["region"],
        "Sector":       df_view["sector"],
        "Barbell":      df_view["barbell_class"],
        "Shares":       df_view["shares"].apply(lambda x: f"{x:,.4f}".rstrip('0').rstrip('.') if x % 1 != 0 else f"{x:,.0f}"),
        "Price (Local)":df_view.apply(fmt_price, axis=1),
        f"MV ({report_ccy})": df_view["mv_report"].apply(fmt_mv),
        f"Cost ({report_ccy})":df_view["cost_usd"].apply(
            lambda x: fmt_mv(x * fx_rate) if report_ccy == "HKD" else fmt_mv(x)),
        "G/L":          df_view.apply(lambda r: fmt_gl(r["gl_report"], r["gl_pct"]), axis=1),
        "Held at":      df_view["brokers"],
        "Price time":   df_view["price_ts"],
    })

    st.dataframe(display, use_container_width=True, hide_index=True,
                 height=min(50 + len(display) * 35, 650))

    # Summary footer
    valid = df_view[df_view["mv_report"].notna()]
    f1, f2, f3 = st.columns(3)
    f1.metric("Filtered MV", f"{ccy_sym}{valid['mv_report'].sum():,.0f}")
    f2.metric("Filtered Cost",
              f"{ccy_sym}{valid['cost_usd'].sum() * (fx_rate if report_ccy=='HKD' else 1):,.0f}")
    gl_filt = valid["gl_report"].sum() if "gl_report" in valid else 0
    f3.metric("Filtered G/L", f"{ccy_sym}{gl_filt:,.0f}")


# ══════════════════════════════════════════════════════════════════
# TAB 2 — BROKER RECONCILIATION
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Broker Reconciliation — Cross-Check View")
    st.caption("Match these numbers against your broker mobile apps.")

    for broker in BROKERS:
        broker_rows = []
        for _, row in port_df.iterrows():
            broker_detail = next(
                (b for b in row["brokers_list"] if b["broker"] == broker), None
            )
            if broker_detail is None:
                continue

            shares_here = broker_detail["shares"]
            cost_here   = broker_detail["avg_cost_local"]
            live_price  = row["live_price"]
            ccy         = row["ccy"]
            sym         = "HK$" if ccy == "HKD" else "$"

            if live_price:
                mv_local_here = shares_here * live_price
                mv_usd_here   = mv_local_here / fx_rate if ccy == "HKD" else mv_local_here
                mv_report_here = mv_usd_here * fx_rate if report_ccy == "HKD" else mv_usd_here
                mv_str = f"{ccy_sym}{mv_report_here:,.0f}"
            else:
                mv_report_here = None
                mv_str = "—"

            broker_rows.append({
                "Ticker":          row["ticker"],
                "Name":            row["name"],
                "Shares":          f"{shares_here:,.4f}".rstrip('0').rstrip('.') if shares_here % 1 != 0 else f"{shares_here:,.0f}",
                "Avg Cost":        f"{sym}{cost_here:,.4f}",
                "Live Price":      f"{sym}{live_price:,.2f}" if live_price else "—",
                f"MV ({report_ccy})": mv_str,
            })

        total_broker_mv = sum(
            float(r[f"MV ({report_ccy})"].replace(ccy_sym, "").replace(",", ""))
            for r in broker_rows if r[f"MV ({report_ccy})"] != "—"
        ) if broker_rows else 0

        n = len(broker_rows)
        label = f"{'🟢' if n > 0 else '⚪'} {broker}  —  {n} position{'s' if n != 1 else ''}  |  est. {ccy_sym}{total_broker_mv:,.0f} {report_ccy}"
        with st.expander(label, expanded=(n > 0)):
            if broker_rows:
                st.dataframe(pd.DataFrame(broker_rows),
                             use_container_width=True, hide_index=True)
            else:
                st.caption("No positions recorded for this broker.")


# ══════════════════════════════════════════════════════════════════
# TAB 3 — ANALYTICS (Barbell + Sector + Region)
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Portfolio Analytics")

    view_mode = st.radio("Group by", ["Barbell Class", "Sector", "Region"],
                          horizontal=True)
    col_map = {"Barbell Class": "barbell_class", "Sector": "sector", "Region": "region"}
    group_col = col_map[view_mode]

    alloc = allocation_by(port_df, group_col)

    c_pie, c_bar = st.columns(2)
    with c_pie:
        COLOR_MAP = {
            # Barbell
            "CORE":        "#2E75B6", "TACTICAL": "#1D9E75", "SPECULATIVE": "#D85A30",
            # Region
            "US":          "#378ADD", "HK": "#1D9E75", "China": "#D85A30",
            "SEA":         "#D4537E", "Other": "#7F77DD",
        }
        colors = [COLOR_MAP.get(g, "#888") for g in alloc[group_col]]
        fig_pie = px.pie(alloc, values="mv_usd", names=group_col,
                         title=f"Allocation by {view_mode}",
                         color_discrete_sequence=colors)
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    with c_bar:
        fig_bar = px.bar(alloc.sort_values("mv_usd"),
                         x="mv_usd", y=group_col, orientation="h",
                         title=f"Market Value by {view_mode} ({report_ccy})",
                         color=group_col, color_discrete_map=COLOR_MAP,
                         text=alloc["pct"].apply(lambda x: f"{x:.1f}%"))
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(showlegend=False, xaxis_title=f"MV ({report_ccy})",
                               yaxis_title="", margin=dict(t=40, b=0, l=0, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)

    # Target progress
    st.divider()
    st.subheader("🎯 Progress to Target")
    prog_cols = st.columns(3)
    with prog_cols[0]:
        pct5 = min(progress["pct_to_5x"], 100)
        st.markdown(f"**5x Target ({ccy_sym}{TARGET_5X_USD/1e6:.2f}M by 2035)**")
        st.progress(pct5 / 100)
        st.caption(f"{pct5:.1f}% there  |  Gap: {ccy_sym}{progress['gap_5x']:,.0f}  |  Need {progress['cagr_needed_5x']:.1f}% CAGR")
    with prog_cols[1]:
        pct10 = min(progress["pct_to_10x"], 100)
        st.markdown(f"**10x Buffer ({ccy_sym}{TARGET_10X_USD/1e6:.2f}M by 2042)**")
        st.progress(pct10 / 100)
        st.caption(f"{pct10:.1f}% there")
    with prog_cols[2]:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=total_mv / 1e6,
            number={"prefix": ccy_sym, "suffix": "M"},
            delta={"reference": TARGET_5X_USD / 1e6, "suffix": "M target"},
            gauge={
                "axis": {"range": [0, TARGET_5X_USD / 1e6]},
                "bar":  {"color": "#2E75B6"},
                "steps": [
                    {"range": [0, TARGET_5X_USD * 0.5 / 1e6], "color": "#1e293b"},
                    {"range": [TARGET_5X_USD * 0.5 / 1e6, TARGET_5X_USD / 1e6], "color": "#0f2d4a"},
                ],
                "threshold": {"line": {"color": "#4ade80", "width": 3},
                              "thickness": 0.75, "value": TARGET_5X_USD / 1e6},
            },
            title={"text": "Portfolio vs 5x Target"},
        ))
        fig_gauge.update_layout(height=220, margin=dict(t=30, b=10, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # Top 10 holdings
    st.divider()
    st.subheader("Top 10 Positions")
    top10 = port_df[port_df["mv_usd"].notna()].nlargest(10, "mv_usd")
    total_port = port_df["mv_usd"].sum()
    top10_display = pd.DataFrame({
        "Ticker":    top10["ticker"],
        "Name":      top10["name"],
        "MV (USD)":  top10["mv_usd"].apply(lambda x: f"${x:,.0f}"),
        "% Port":    (top10["mv_usd"] / total_port * 100).apply(lambda x: f"{x:.1f}%"),
        "G/L":       top10["gl_usd"].apply(lambda x: f"${x:+,.0f}" if pd.notna(x) else "—"),
        "G/L %":     top10["gl_pct"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"),
        "Barbell":   top10["barbell_class"],
        "Region":    top10["region"],
    })
    st.dataframe(top10_display, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# TAB 4 — ALERTS (Concentration + Compliance)
# ══════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("⚠️ Alerts & Compliance")

    # Concentration
    st.markdown("#### Concentration Alerts  (positions > 5% of portfolio)")
    conc = concentration_alerts(port_df)
    if not conc.empty:
        conc_display = pd.DataFrame({
            "Ticker":       conc["ticker"],
            "Name":         conc["name"],
            "Sector":       conc["sector"],
            "Region":       conc["region"],
            "MV (USD)":     conc["mv_usd"].apply(lambda x: f"${x:,.0f}"),
            "% Portfolio":  conc["pct_of_port"].apply(lambda x: f"{x:.1f}%"),
            "Held at":      conc["brokers"],
        })
        st.dataframe(conc_display, use_container_width=True, hide_index=True)
    else:
        st.success("No single position exceeds 5% of portfolio.")

    # Cross-custodian fragmentation
    st.markdown("#### Cross-Custodian Fragmentation")
    multi = port_df[port_df["brokers"].str.contains(",")].copy()
    multi = multi.sort_values("mv_usd", ascending=False, na_position="last")
    if not multi.empty:
        m_display = pd.DataFrame({
            "Ticker":    multi["ticker"],
            "Name":      multi["name"],
            "MV (USD)":  multi["mv_usd"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—"),
            "Held at":   multi["brokers"],
        })
        st.dataframe(m_display, use_container_width=True, hide_index=True)

    # Compliance
    st.markdown("#### Compliance Check")
    comp = compliance_check(port_df)
    if not comp.empty:
        st.error(f"⛔ {len(comp)} compliance issue(s) found")
        st.dataframe(comp[["ticker", "name", "sector", "flags"]],
                     use_container_width=True, hide_index=True)
    else:
        st.success("✅ No compliance violations detected.")

    # Positions with no price
    st.markdown("#### Positions Missing Live Price")
    no_price = port_df[port_df["live_price"].isna()][["ticker", "name", "sector", "price_error"]]
    if not no_price.empty:
        st.warning(f"{len(no_price)} position(s) have no live price")
        st.dataframe(no_price, use_container_width=True, hide_index=True)
    else:
        st.success("✅ All positions have live prices.")


# ══════════════════════════════════════════════════════════════════
# TAB 5 — TRADE ENTRY
# ══════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("✏️ Trade Entry")
    st.caption("Enter trades manually. The app calculates new cost basis and updates Google Sheets automatically.")

    entry_mode = st.radio("Entry mode", ["Single trade", "Upload activity CSV"],
                           horizontal=True)

    if entry_mode == "Single trade":
        with st.form("trade_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                broker = st.selectbox("Broker", BROKERS)
                action = st.radio("Action", ["BUY", "SELL"], horizontal=True)
            with c2:
                ticker = st.text_input("Ticker", placeholder="e.g. MSFT or 0700.HK")
                ccy    = st.radio("Currency", ["USD", "HKD"], horizontal=True)
            with c3:
                trade_date = st.date_input("Trade date", value=datetime.date.today())
                settle_date= st.date_input("Settle date",
                                            value=datetime.date.today() + datetime.timedelta(days=2))

            c4, c5, c6 = st.columns(3)
            with c4:
                shares = st.number_input("Shares", min_value=0.0, step=1.0, format="%.4f")
            with c5:
                price  = st.number_input("Price (local ccy)", min_value=0.0, step=0.01, format="%.4f")
            with c6:
                comm   = st.number_input("Commission", min_value=0.0, step=0.01, format="%.2f")

            notes  = st.text_input("Notes (optional)")
            gross  = shares * price

            # Preview
            if shares > 0 and price > 0:
                st.info(f"**Preview:** {action} {shares:,.2f} × "
                        f"{'HK$' if ccy=='HKD' else '$'}{price:,.4f} = "
                        f"{'HK$' if ccy=='HKD' else '$'}{gross:,.2f}  "
                        f"(+ {'HK$' if ccy=='HKD' else '$'}{comm:.2f} commission)")

                # Show impact on existing position
                existing = port_df[port_df["ticker"] == ticker.upper().strip()]
                if not existing.empty and action == "BUY":
                    cur_shares = existing["shares"].iloc[0]
                    cur_cost   = existing["cost_local"].iloc[0]
                    new_avg    = calc_new_avg_cost(cur_shares, cur_cost, shares, price)
                    new_total  = cur_shares + shares
                    st.success(f"**Cost basis impact:** "
                               f"Current avg {'HK$' if ccy=='HKD' else '$'}{cur_cost:,.4f} → "
                               f"New avg {'HK$' if ccy=='HKD' else '$'}{new_avg:,.4f}  |  "
                               f"Total shares: {cur_shares:,.2f} → {new_total:,.2f}")

            submitted = st.form_submit_button("✅ Confirm Trade", type="primary")
            if submitted:
                if not ticker.strip():
                    st.error("Please enter a ticker symbol.")
                elif shares <= 0 or price <= 0:
                    st.error("Shares and price must be greater than zero.")
                else:
                    trade = {
                        "trade_date":  str(trade_date),
                        "settle_date": str(settle_date),
                        "broker":      broker,
                        "ticker":      ticker.strip().upper(),
                        "action":      action,
                        "shares":      shares,
                        "price_local": price,
                        "ccy":         ccy,
                        "commission":  comm,
                        "fx_rate":     fx_rate if ccy == "HKD" else 1.0,
                        "gross_usd":   round(gross / fx_rate, 2) if ccy == "HKD" else round(gross, 2),
                        "notes":       notes,
                    }
                    with st.spinner("Writing to Google Sheets…"):
                        append_trades([trade], source="manual")
                    st.success(f"✅ Trade recorded: {action} {shares:,.2f} {ticker} @ "
                               f"{'HK$' if ccy=='HKD' else '$'}{price:,.4f}")
                    st.cache_data.clear()
                    st.rerun()

    else:  # Upload CSV
        st.markdown("Upload a transaction CSV from any of the active brokers:")
        broker_up = st.selectbox("Which broker?", ACTIVE_BROKERS)
        uploaded  = st.file_uploader(f"Upload {broker_up} activity CSV",
                                      type=["csv"], key="upload_csv")
        if uploaded:
            from parsers import PARSER_MAP
            try:
                parser = PARSER_MAP[broker_up]
                trades = parser(uploaded)
                st.success(f"✅ Parsed {len(trades)} trades from {broker_up}")

                # Preview table
                preview_df = pd.DataFrame(trades)[
                    ["trade_date", "ticker", "action", "shares", "price_local", "ccy", "commission"]
                ]
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

                if st.button("📥 Import all trades to Google Sheets", type="primary"):
                    with st.spinner("Writing to Google Sheets…"):
                        append_trades(trades, source=f"{broker_up.lower()}_upload")
                    st.success(f"✅ {len(trades)} trades imported. Portfolio recalculated.")
                    st.cache_data.clear()
                    st.rerun()

            except Exception as e:
                st.error(f"Parse error: {e}")
                st.caption("Check that you exported the correct report type. See SETUP.md for format details.")

    # Recent trades log
    st.divider()
    st.markdown("#### Recent Trades Log")
    if SHEETS_AVAILABLE:
        try:
            trades_df = read_trades()
            if not trades_df.empty:
                recent = trades_df.sort_values("trade_date", ascending=False).head(20)
                st.dataframe(
                    recent[["trade_date", "broker", "ticker", "action",
                             "shares", "price_local", "ccy", "commission", "source"]],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.caption("No trades recorded yet.")
        except Exception as e:
            st.caption(f"Could not load trade log: {e}")
    else:
        st.caption("Connect Google Sheets to see trade log (see SETUP.md).")


# ══════════════════════════════════════════════════════════════════
# TAB 6 — EXPORT
# ══════════════════════════════════════════════════════════════════
with tab6:
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    st.subheader("📄 Export Portfolio Report")
    st.caption("Downloads a formatted Excel workbook with all tabs. Open in Excel → File → Print → Save as PDF.")

    def build_excel(port_df, summary, fx_rate, report_ccy) -> bytes:
        wb = openpyxl.Workbook()

        # ── Styles ────────────────────────────────────────────────
        hdr_font    = Font(bold=True, color="FFFFFF", size=11)
        hdr_fill    = PatternFill("solid", fgColor="1F3864")
        alt_fill    = PatternFill("solid", fgColor="EEF2F7")
        title_font  = Font(bold=True, size=13)
        border_side = Side(style="thin", color="CCCCCC")
        thin_border = Border(bottom=border_side)
        sym         = "HK$" if report_ccy == "HKD" else "$"

        def style_header_row(ws, row_num, ncols):
            for c in range(1, ncols + 1):
                cell = ws.cell(row=row_num, column=c)
                cell.font = hdr_font
                cell.fill = hdr_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        def style_data_rows(ws, start_row, end_row, ncols):
            for r in range(start_row, end_row + 1):
                fill = alt_fill if r % 2 == 0 else None
                for c in range(1, ncols + 1):
                    cell = ws.cell(row=r, column=c)
                    if fill:
                        cell.fill = fill
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical="center")

        def autofit(ws, min_w=8, max_w=40):
            for col in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in col), default=0)
                ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(max_len + 2, min_w), max_w)

        # ── Sheet 1: Summary ──────────────────────────────────────
        ws1 = wb.active
        ws1.title = "Portfolio Summary"
        ws1.row_dimensions[1].height = 30

        import datetime as _dt
        hkt = _dt.timezone(_dt.timedelta(hours=8))
        now_str = _dt.datetime.now(hkt).strftime("%Y-%m-%d %H:%M HKT")

        summary_data = [
            ["Project Apex 2035 — Portfolio Report", ""],
            [f"Generated", now_str],
            [f"Report Currency", report_ccy],
            [f"FX Rate (USD/HKD)", f"{fx_rate:.4f}"],
            ["", ""],
            ["METRIC", "VALUE"],
            ["Total Market Value", f"{sym}{summary['total_mv']:,.0f}"],
            ["Total Cost Basis", f"{sym}{summary['total_cost']:,.0f}"],
            ["Unrealized G/L", f"{sym}{summary['total_gl']:+,.0f}"],
            ["G/L %", f"{summary['total_gl_pct']:+.2f}%"],
            ["Number of Positions", summary["n_positions"]],
            ["5x Target", f"{sym}{summary['target_5x']:,.0f}"],
            ["% to 5x Target", f"{summary['pct_to_5x']:.1f}%"],
            ["10x Target", f"{sym}{summary['target_10x']:,.0f}"],
            ["% to 10x Target", f"{summary['pct_to_10x']:.1f}%"],
        ]
        for i, row in enumerate(summary_data, 1):
            ws1.cell(i, 1, row[0])
            ws1.cell(i, 2, row[1])
        ws1.cell(1, 1).font = title_font
        style_header_row(ws1, 6, 2)
        style_data_rows(ws1, 7, len(summary_data), 2)
        ws1.column_dimensions["A"].width = 28
        ws1.column_dimensions["B"].width = 24

        # ── Sheet 2: All Positions ────────────────────────────────
        ws2 = wb.create_sheet("All Positions")
        headers = ["Ticker", "Name", "Region", "Sector", "Barbell",
                   "CCY", "Shares", "Avg Cost (Local)", "Live Price",
                   f"MV ({report_ccy})", f"Cost ({report_ccy})",
                   "G/L (USD)", "G/L %", "Held At", "Price Time"]
        for c, h in enumerate(headers, 1):
            ws2.cell(1, c, h)
        style_header_row(ws2, 1, len(headers))
        ws2.row_dimensions[1].height = 28

        df_sorted = port_df.sort_values("mv_usd", ascending=False, na_position="last")
        for r, (_, row) in enumerate(df_sorted.iterrows(), 2):
            mv_r  = row["mv_report"]
            cost_r = row["cost_usd"] * (fx_rate if report_ccy == "HKD" else 1) if row["cost_usd"] else None
            ws2.cell(r, 1,  row["ticker"])
            ws2.cell(r, 2,  row["name"])
            ws2.cell(r, 3,  row["region"])
            ws2.cell(r, 4,  row["sector"])
            ws2.cell(r, 5,  row["barbell_class"])
            ws2.cell(r, 6,  row["ccy"])
            ws2.cell(r, 7,  row["shares"])
            ws2.cell(r, 8,  row["cost_local"])
            ws2.cell(r, 9,  row["live_price"])
            ws2.cell(r, 10, mv_r)
            ws2.cell(r, 11, cost_r)
            ws2.cell(r, 12, row["gl_usd"])
            ws2.cell(r, 13, f"{row['gl_pct']:+.1f}%" if row["gl_pct"] is not None and str(row["gl_pct"]) != "nan" else "—")
            ws2.cell(r, 14, row["brokers"])
            ws2.cell(r, 15, row["price_ts"])
            # Number formats
            for col in [7, 8, 9, 10, 11, 12]:
                cell = ws2.cell(r, col)
                if cell.value is not None:
                    cell.number_format = '#,##0.00'
        style_data_rows(ws2, 2, len(df_sorted) + 1, len(headers))
        autofit(ws2)

        # ── Sheet 3: By Broker ────────────────────────────────────
        ws3 = wb.create_sheet("By Broker")
        broker_headers = ["Broker", "Ticker", "Name", "Shares",
                          "Avg Cost (Local)", "Live Price", f"MV ({report_ccy})"]
        for c, h in enumerate(broker_headers, 1):
            ws3.cell(1, c, h)
        style_header_row(ws3, 1, len(broker_headers))
        ws3.row_dimensions[1].height = 28

        r = 2
        for broker in BROKERS:
            for _, row in df_sorted.iterrows():
                b_detail = next((b for b in row["brokers_list"] if b["broker"] == broker), None)
                if b_detail is None:
                    continue
                sh = b_detail["shares"]
                lp = row["live_price"]
                mv_here = None
                if lp and sh:
                    mv_local_h = sh * lp
                    mv_usd_h   = mv_local_h / fx_rate if row["ccy"] == "HKD" else mv_local_h
                    mv_here    = mv_usd_h * fx_rate if report_ccy == "HKD" else mv_usd_h
                ws3.cell(r, 1, broker)
                ws3.cell(r, 2, row["ticker"])
                ws3.cell(r, 3, row["name"])
                ws3.cell(r, 4, sh)
                ws3.cell(r, 5, b_detail["avg_cost_local"])
                ws3.cell(r, 6, lp)
                ws3.cell(r, 7, mv_here)
                for col in [4, 5, 6, 7]:
                    cell = ws3.cell(r, col)
                    if cell.value is not None:
                        cell.number_format = '#,##0.00'
                r += 1
        style_data_rows(ws3, 2, r - 1, len(broker_headers))
        autofit(ws3)

        # ── Sheet 4: By Sector ────────────────────────────────────
        ws4 = wb.create_sheet("By Sector")
        alloc_h = ["Group", "Sector", "Ticker", "Name", f"MV ({report_ccy})", "% Portfolio"]
        for c, h in enumerate(alloc_h, 1):
            ws4.cell(1, c, h)
        style_header_row(ws4, 1, len(alloc_h))
        ws4.row_dimensions[1].height = 28

        total_mv_usd = port_df["mv_usd"].sum()
        df_sec = df_sorted[df_sorted["mv_usd"].notna()].copy()
        r = 2
        for barbell in ["CORE", "TACTICAL", "SPECULATIVE"]:
            grp = df_sec[df_sec["barbell_class"] == barbell]
            for _, row in grp.iterrows():
                mv_r = row["mv_report"]
                pct  = row["mv_usd"] / total_mv_usd * 100 if total_mv_usd else 0
                ws4.cell(r, 1, barbell)
                ws4.cell(r, 2, row["sector"])
                ws4.cell(r, 3, row["ticker"])
                ws4.cell(r, 4, row["name"])
                ws4.cell(r, 5, mv_r)
                ws4.cell(r, 6, f"{pct:.2f}%")
                if ws4.cell(r, 5).value is not None:
                    ws4.cell(r, 5).number_format = '#,##0'
                r += 1
        style_data_rows(ws4, 2, r - 1, len(alloc_h))
        autofit(ws4)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("📥 Generate Excel Report", type="primary"):
            xlsx_bytes = build_excel(port_df, summary, fx_rate, report_ccy)
            st.download_button(
                label="⬇️ Download Excel (.xlsx)",
                data=xlsx_bytes,
                file_name=f"Apex2035_Portfolio_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    with col_info:
        st.markdown("""
        **What's included:**
        - **Sheet 1:** Portfolio Summary (totals, targets, FX)
        - **Sheet 2:** All Positions — sorted by MV, all metrics
        - **Sheet 3:** By Broker — every position per broker
        - **Sheet 4:** By Sector/Barbell — allocation breakdown

        **To save as PDF:** Open in Excel → File → Print → Microsoft Print to PDF
        """)
