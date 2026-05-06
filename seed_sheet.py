#!/usr/bin/env python3
"""
seed_sheet.py — ONE-TIME SETUP SCRIPT
Run this once to initialise your Google Sheet with current holdings.

Usage:
    python seed_sheet.py --creds path/to/service_account.json

The script will:
  1. Create or clear the 4 required worksheets
  2. Write column headers
  3. Seed Holdings_Master with all 70 current positions
  4. Leave Trades_Ledger and Broker_Snapshots empty (ready for use)
"""
import json
import argparse
import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import (
    GSHEET_NAME, SHEET_HOLDINGS, SHEET_TRADES,
    SHEET_BROKER_SNAPSHOTS, INITIAL_POSITIONS,
    HKD_USD_RATE,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HOLDINGS_COLS = [
    "ticker", "name", "region", "sector", "barbell_class", "ccy",
    "total_shares", "avg_cost_local", "avg_cost_usd",
    "brokers_json", "manual_price", "compliance_flag",
    "lockup_expiry", "notes", "last_updated",
]
TRADES_COLS = [
    "trade_id", "trade_date", "settle_date", "broker", "ticker",
    "action", "shares", "price_local", "ccy", "gross_local",
    "commission", "fx_rate", "gross_usd", "source", "notes", "uploaded_at",
]
SNAPSHOT_COLS = [
    "snapshot_date", "broker", "total_mv_local", "ccy",
    "total_mv_usd", "cash_balance_usd", "notes",
]
CONFIG_ROWS = [
    ["param_key", "param_value", "description"],
    ["target_5x_usd",          "13350000",  "Garden Terrace 5x target (USD)"],
    ["target_10x_usd",         "26700000",  "Maximum buffer 10x by 2042 (USD)"],
    ["target_year_5x",         "2035",      "Year for 5x target"],
    ["target_year_10x",        "2042",      "Year for 10x buffer"],
    ["min_hold_days_stock",    "30",        "Minimum holding period stocks (days)"],
    ["min_hold_days_gold",     "90",        "Minimum holding period gold (days)"],
    ["etf_hold_exempt",        "TRUE",      "ETFs exempt from holding period"],
    ["us_div_withholding_pct", "30",        "US dividend withholding tax %"],
    ["hk_capital_gains_tax",   "0",         "HK capital gains tax %"],
    ["banned_sectors",         "Banking,Insurance", "Banned sector keywords"],
    ["concentration_alert_pct","5",         "Flag position if > X% of portfolio"],
    ["hkd_usd_fallback",       str(HKD_USD_RATE), "Fallback FX rate if live unavailable"],
    ["price_source",           "yfinance",  "yfinance | lseg"],
    ["price_cache_seconds",    "300",       "Price cache TTL in seconds"],
]


def get_or_create_worksheet(wb, name: str, rows=2000, cols=20):
    try:
        ws = wb.worksheet(name)
        ws.clear()
        print(f"  Cleared existing sheet: {name}")
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(title=name, rows=rows, cols=cols)
        print(f"  Created new sheet: {name}")
    return ws


def build_holdings_rows() -> list[list]:
    """Convert INITIAL_POSITIONS → list of rows matching HOLDINGS_COLS."""
    rows = []
    now = datetime.datetime.utcnow().isoformat()

    for pos in INITIAL_POSITIONS:
        brokers = pos.get("brokers", [])

        # Total shares = sum across all brokers
        total_shares = sum(b["shares"] for b in brokers)

        # Weighted average cost (local currency)
        total_cost_weight = sum(b["shares"] * b["avg_cost_local"] for b in brokers)
        avg_cost_local = total_cost_weight / total_shares if total_shares else 0

        # Convert to USD
        if pos["ccy"] == "HKD":
            avg_cost_usd = avg_cost_local / HKD_USD_RATE
        else:
            avg_cost_usd = avg_cost_local

        # Brokers JSON
        brokers_json = json.dumps(brokers)

        row = {
            "ticker":         pos["ticker"],
            "name":           pos["name"],
            "region":         pos["region"],
            "sector":         pos["sector"],
            "barbell_class":  pos["barbell_class"],
            "ccy":            pos["ccy"],
            "total_shares":   round(total_shares, 6),
            "avg_cost_local": round(avg_cost_local, 4),
            "avg_cost_usd":   round(avg_cost_usd, 4),
            "brokers_json":   brokers_json,
            "manual_price":   "",
            "compliance_flag":"",
            "lockup_expiry":  "",
            "notes":          "",
            "last_updated":   now,
        }
        rows.append([row[c] for c in HOLDINGS_COLS])

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--creds", required=True,
                        help="Path to Google service account JSON file")
    parser.add_argument("--sheet-id", default=None,
                        help="Existing Google Sheet ID to write into (open by ID)")
    args = parser.parse_args()

    print(f"\n🚀 Seeding Google Sheet: '{GSHEET_NAME}'")
    print(f"   Using credentials: {args.creds}\n")

    creds = Credentials.from_service_account_file(args.creds, scopes=SCOPES)
    client = gspread.authorize(creds)

    # Open or create workbook
    if args.sheet_id:
        wb = client.open_by_key(args.sheet_id)
        print(f"✓ Opened workbook by ID: {args.sheet_id}")
    else:
        try:
            wb = client.open(GSHEET_NAME)
            print(f"✓ Opened existing workbook: {GSHEET_NAME}")
        except gspread.SpreadsheetNotFound:
            wb = client.create(GSHEET_NAME)
            print(f"✓ Created new workbook: {GSHEET_NAME}")
            # Share with your personal Google account so you can view it
            print("  ⚠  Share this sheet with your Google account manually in Drive.")

    print("\n── Setting up worksheets ─────────────────────────────")

    # 1. Holdings_Master
    ws_h = get_or_create_worksheet(wb, SHEET_HOLDINGS)
    holding_rows = build_holdings_rows()
    ws_h.update([HOLDINGS_COLS] + holding_rows, value_input_option="USER_ENTERED")
    print(f"  ✓ Holdings_Master: {len(holding_rows)} positions written")

    # 2. Trades_Ledger
    ws_t = get_or_create_worksheet(wb, SHEET_TRADES)
    ws_t.update([TRADES_COLS], value_input_option="USER_ENTERED")
    print(f"  ✓ Trades_Ledger: headers written (empty, ready for use)")

    # 3. Config
    ws_c = get_or_create_worksheet(wb, "Config")
    ws_c.update(CONFIG_ROWS, value_input_option="USER_ENTERED")
    print(f"  ✓ Config: {len(CONFIG_ROWS)-1} parameters written")

    # 4. Broker_Snapshots
    ws_s = get_or_create_worksheet(wb, SHEET_BROKER_SNAPSHOTS)
    ws_s.update([SNAPSHOT_COLS], value_input_option="USER_ENTERED")
    print(f"  ✓ Broker_Snapshots: headers written (empty, ready for use)")

    # Print sheet URL
    url = f"https://docs.google.com/spreadsheets/d/{wb.id}"
    print(f"\n✅ Done! Your Google Sheet is ready:")
    print(f"   {url}")
    print(f"\n📋 Next steps:")
    print(f"   1. Open the URL above and verify the data looks correct")
    print(f"   2. Share the sheet with your service account email (already done if you used the same account)")
    print(f"   3. Copy the Sheet ID from the URL (the long string between /d/ and /edit)")
    print(f"   4. Add your credentials to Streamlit secrets (see SETUP.md)")
    print(f"   5. Run: streamlit run app.py")


if __name__ == "__main__":
    main()
