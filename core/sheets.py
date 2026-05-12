# core/sheets.py — Google Sheets read/write via gspread
import json
import datetime
import pandas as pd
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from config import (
    GSHEET_NAME, SHEET_HOLDINGS, SHEET_TRADES,
    SHEET_BROKER_SNAPSHOTS,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Auth ──────────────────────────────────────────────────────────
@st.cache_resource
def get_client() -> gspread.Client:
    """
    Authenticates using service account JSON stored in Streamlit secrets.
    In secrets.toml:
        [gcp_service_account]
        type = "service_account"
        project_id = "..."
        private_key_id = "..."
        private_key = "..."
        client_email = "..."
        ... (full service account JSON)
    """
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource
def get_sheet(sheet_name: str) -> gspread.Worksheet:
    client = get_client()
    wb = client.open(GSHEET_NAME)
    return wb.worksheet(sheet_name)


# ── Holdings ──────────────────────────────────────────────────────
HOLDINGS_COLS = [
    "ticker", "name", "region", "sector", "barbell_class", "ccy",
    "total_shares", "avg_cost_local", "avg_cost_usd",
    "brokers_json",          # JSON string: [{broker, shares, avg_cost_local}]
    "manual_price",          # override price (for STRUCT-CITI etc.)
    "compliance_flag",       # "" | "HOLD_VIOLATION" | "BANNED_SECTOR"
    "lockup_expiry",         # ISO date or ""
    "notes",
    "last_updated",
]

@st.cache_data(ttl=300)
def read_holdings() -> pd.DataFrame:
    """Read Holdings_Master sheet → DataFrame. Cached 5 min."""
    ws = get_sheet(SHEET_HOLDINGS)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=HOLDINGS_COLS)
    df = pd.DataFrame(data)
    df["total_shares"]    = pd.to_numeric(df["total_shares"],    errors="coerce").fillna(0)
    df["avg_cost_local"]  = pd.to_numeric(df["avg_cost_local"],  errors="coerce").fillna(0)
    df["avg_cost_usd"]    = pd.to_numeric(df["avg_cost_usd"],    errors="coerce").fillna(0)
    df["manual_price"]    = pd.to_numeric(df["manual_price"],    errors="coerce")
    return df


def write_holdings(df: pd.DataFrame):
    """Overwrite Holdings_Master with DataFrame. Clears and re-writes."""
    ws = get_sheet(SHEET_HOLDINGS)
    ws.clear()
    ws.update([df.columns.tolist()] + df.fillna("").values.tolist())


def upsert_holding(row: dict):
    """
    Insert or update a single ticker row in Holdings_Master.
    Matches on ticker column.
    """
    df = read_holdings()
    mask = df["ticker"] == row["ticker"]
    row["last_updated"] = datetime.datetime.utcnow().isoformat()

    if mask.any():
        for col, val in row.items():
            if col in df.columns:
                df.loc[mask, col] = val
    else:
        new_row = {c: row.get(c, "") for c in HOLDINGS_COLS}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    write_holdings(df)
    # Clear Streamlit cache so next read is fresh
    read_holdings.clear()


# ── Trades Ledger ─────────────────────────────────────────────────
TRADES_COLS = [
    "trade_id",       # UUID / timestamp-based
    "trade_date",
    "settle_date",
    "broker",
    "ticker",
    "action",         # BUY | SELL
    "shares",
    "price_local",
    "ccy",
    "gross_local",
    "commission",
    "fx_rate",
    "gross_usd",
    "source",         # "manual" | "schwab_upload" | "ibkr_upload" | etc.
    "notes",
    "uploaded_at",
]

@st.cache_data(ttl=300)
def read_trades() -> pd.DataFrame:
    ws = get_sheet(SHEET_TRADES)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=TRADES_COLS)
    df = pd.DataFrame(data)
    num_cols = ["shares", "price_local", "gross_local", "commission", "fx_rate", "gross_usd"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def append_trades(trades: list[dict], source: str = "manual"):
    """
    Append a list of trade dicts to Trades_Ledger.
    Also triggers recalculate_holdings() to update Holdings_Master.
    """
    import uuid
    ws = get_sheet(SHEET_TRADES)
    now = datetime.datetime.utcnow().isoformat()
    rows = []
    for t in trades:
        t["trade_id"]    = str(uuid.uuid4())[:8]
        t["source"]      = source
        t["uploaded_at"] = now
        t["gross_local"] = round(t["shares"] * t["price_local"], 4)
        rows.append([t.get(c, "") for c in TRADES_COLS])
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    # Recalculate affected positions
    tickers = list({t["ticker"] for t in trades})
    for ticker in tickers:
        recalculate_holding(ticker)
    read_trades.clear()


def recalculate_holding(ticker: str):
    """
    Re-derives total_shares and avg_cost_local for a ticker
    from the full Trades_Ledger. Weighted average cost basis (FIFO not used —
    HK zero CGT makes average cost simpler and sufficient).
    """
    from core.prices import get_hkd_usd_rate
    trades_df = read_trades()
    t = trades_df[trades_df["ticker"] == ticker].copy()
    if t.empty:
        return

    holdings_df = read_holdings()
    existing = holdings_df[holdings_df["ticker"] == ticker]

    total_shares = 0.0
    total_cost   = 0.0

    for _, row in t.sort_values("trade_date").iterrows():
        if row["action"] == "BUY":
            # Weighted average
            new_cost = total_shares * total_cost + row["shares"] * row["price_local"]
            total_shares += row["shares"]
            total_cost    = new_cost / total_shares if total_shares else 0
        elif row["action"] == "SELL":
            total_shares -= row["shares"]
            # Cost basis unchanged on sells (HK convention)
            if total_shares < 0:
                total_shares = 0

    fx = get_hkd_usd_rate()
    ccy = t["ccy"].iloc[0]
    avg_cost_usd = total_cost / fx if ccy == "HKD" else total_cost

    if not existing.empty:
        brokers_json = existing["brokers_json"].iloc[0]
    else:
        brokers_json = "[]"

    upsert_holding({
        "ticker":         ticker,
        "total_shares":   round(total_shares, 6),
        "avg_cost_local": round(total_cost, 4),
        "avg_cost_usd":   round(avg_cost_usd, 4),
        "brokers_json":   brokers_json,
    })


# ── Broker Snapshots ──────────────────────────────────────────────
SNAPSHOT_COLS = [
    "snapshot_date", "broker", "total_mv_local", "ccy",
    "total_mv_usd", "cash_balance_usd", "notes",
]

def append_broker_snapshot(rows: list[dict]):
    ws = get_sheet(SHEET_BROKER_SNAPSHOTS)
    data = [[r.get(c, "") for c in SNAPSHOT_COLS] for r in rows]
    ws.append_rows(data, value_input_option="USER_ENTERED")


def read_broker_snapshots() -> pd.DataFrame:
    ws = get_sheet(SHEET_BROKER_SNAPSHOTS)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=SNAPSHOT_COLS)
    return pd.DataFrame(data)


# ── Watchlist ─────────────────────────────────────────────────────
WATCHLIST_COLS = ["ticker", "date_added", "price", "score", "verdict"]

def append_watchlist(ticker: str, price, score: int, verdict: str):
    """
    Appends a ticker to the Watchlist tab (creates the tab if missing).
    Returns True on success, error string on failure.
    """
    try:
        client = get_client()
        wb     = client.open(GSHEET_NAME)
        try:
            ws = wb.worksheet("Watchlist")
        except gspread.exceptions.WorksheetNotFound:
            ws = wb.add_worksheet("Watchlist", rows=1000, cols=10)
            ws.append_row(WATCHLIST_COLS)
        row = [
            ticker,
            datetime.date.today().isoformat(),
            float(price) if price else "",
            int(score),
            verdict,
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        return str(e)


# ── Portfolio History ─────────────────────────────────────────────
HISTORY_COLS = [
    "date", "total_mv_usd", "total_cost_usd",
    "total_gl_usd", "gl_pct", "hkd_usd_rate", "notes",
]
_HISTORY_SHEET = "Portfolio_History"


def _history_ws():
    client = get_client()
    wb = client.open(GSHEET_NAME)
    try:
        return wb.worksheet(_HISTORY_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = wb.add_worksheet(_HISTORY_SHEET, rows=2000, cols=len(HISTORY_COLS))
        ws.append_row(HISTORY_COLS)
        return ws


def append_portfolio_snapshot(snapshot: dict):
    """Save today's portfolio value. Skips silently if today already recorded."""
    try:
        ws   = _history_ws()
        today = datetime.date.today().isoformat()
        data = ws.get_all_records()
        if any(r.get("date") == today for r in data):
            return  # already saved today
        ws.append_row([
            today,
            round(snapshot.get("total_mv_usd",   0), 2),
            round(snapshot.get("total_cost_usd",  0), 2),
            round(snapshot.get("total_gl_usd",    0), 2),
            round(snapshot.get("gl_pct",          0), 4),
            round(snapshot.get("hkd_usd_rate", 7.834), 4),
            snapshot.get("notes", ""),
        ], value_input_option="USER_ENTERED")
    except Exception:
        pass  # never crash the app for a snapshot


@st.cache_data(ttl=300)
def read_portfolio_history() -> "pd.DataFrame":
    try:
        ws   = _history_ws()
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=HISTORY_COLS)
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["total_mv_usd", "total_cost_usd", "total_gl_usd",
                    "gl_pct", "hkd_usd_rate"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.sort_values("date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=HISTORY_COLS)


# ── Conviction Log ────────────────────────────────────────────────
CONVICTION_COLS = [
    "conviction_id", "entry_date", "ticker", "name", "action",
    "entry_price", "position_size_usd", "max_size_cap_usd",
    "thesis", "bull_case", "bear_case",
    "falsification_price", "time_horizon_months",
    "opportunity_cost", "status", "review_date",
    "outcome_notes", "grade",
]
_CONVICTION_SHEET = "Conviction_Log"


def _conviction_ws():
    """Return (or create) the Conviction_Log worksheet."""
    client = get_client()
    wb     = client.open(GSHEET_NAME)
    try:
        return wb.worksheet(_CONVICTION_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = wb.add_worksheet(_CONVICTION_SHEET, rows=2000,
                               cols=len(CONVICTION_COLS))
        ws.append_row(CONVICTION_COLS)
        return ws


def read_convictions() -> pd.DataFrame:
    """Read all rows from Conviction_Log. Returns empty DataFrame on failure."""
    try:
        ws   = _conviction_ws()
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=CONVICTION_COLS)
        df = pd.DataFrame(data)
        for col in ["entry_price", "position_size_usd", "max_size_cap_usd",
                    "falsification_price", "time_horizon_months"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(columns=CONVICTION_COLS)


def append_conviction(row: dict):
    """
    Append a new conviction to the log.
    Returns True on success, error string on failure.
    """
    import uuid
    try:
        ws = _conviction_ws()
        row.setdefault("conviction_id",   str(uuid.uuid4())[:8])
        row.setdefault("entry_date",      datetime.date.today().isoformat())
        row.setdefault("status",          "ACTIVE")
        row.setdefault("review_date",     "")
        row.setdefault("outcome_notes",   "")
        row.setdefault("grade",           "")
        values = [str(row.get(c, "")) for c in CONVICTION_COLS]
        ws.append_row(values, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        return str(e)


def update_conviction(conviction_id: str, updates: dict):
    """
    Update specific fields for a conviction by ID.
    Returns True on success, error string on failure.
    """
    try:
        ws   = _conviction_ws()
        data = ws.get_all_records()
        for i, record in enumerate(data, 2):  # row 1 = header
            if record.get("conviction_id") == conviction_id:
                for col_name, value in updates.items():
                    if col_name in CONVICTION_COLS:
                        col_idx = CONVICTION_COLS.index(col_name) + 1
                        ws.update_cell(i, col_idx, str(value))
                return True
        return "conviction_id not found"
    except Exception as e:
        return str(e)
