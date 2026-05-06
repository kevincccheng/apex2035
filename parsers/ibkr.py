# parsers/ibkr.py — IBKR Activity Statement CSV parser
import io
import pandas as pd
from dateutil.parser import parse as parse_date


def parse_ibkr(file) -> list[dict]:
    """
    Parses IBKR Activity Statement CSV (exported from Client Portal or TWS).
    The CSV has multiple sections; we look for the 'Trades' section.
    """
    content = file.read().decode("utf-8", errors="replace")
    trades = []
    lines = content.splitlines()

    # IBKR CSV: each section starts with a header like:
    # Trades,Header,DataDiscriminator,Asset Category,Currency,...
    in_trades = False
    col_names = []

    for line in lines:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if not parts:
            continue

        # Section header row
        if parts[0] == "Trades" and parts[1] == "Header":
            col_names = parts[2:]  # skip "Trades", "Header"
            in_trades = True
            continue

        if in_trades:
            if parts[0] != "Trades" or parts[1] != "Data":
                if parts[0] == "Trades" and parts[1] == "SubTotal":
                    continue
                in_trades = False
                continue

            row = dict(zip(col_names, parts[2:]))
            asset_cat = row.get("Asset Category", "")
            if asset_cat not in ("Stocks", "Equity and Index Options"):
                continue

            action_raw = row.get("Buy/Sell", "").strip()
            if action_raw not in ("BUY", "SELL", "B", "S"):
                continue
            action = "BUY" if action_raw in ("BUY", "B") else "SELL"

            symbol = row.get("Symbol", "").strip()
            ccy    = row.get("Currency", "USD").strip()

            try:
                qty    = abs(float(row.get("Quantity", 0).replace(",", "")))
                price  = abs(float(row.get("T. Price", 0).replace(",", "")))
                comm   = abs(float(row.get("Comm/Fee", 0).replace(",", "") or 0))
                date   = parse_date(row.get("Date/Time", "").split(",")[0]).strftime("%Y-%m-%d")
            except Exception:
                continue

            if qty == 0 or price == 0:
                continue

            # HK stocks: IBKR uses plain number e.g. "700" → convert to "0700.HK"
            if ccy == "HKD" and not symbol.endswith(".HK"):
                symbol = symbol.zfill(4) + ".HK"

            trades.append({
                "trade_date":  date,
                "settle_date": "",
                "broker":      "IBKR",
                "ticker":      symbol,
                "action":      action,
                "shares":      qty,
                "price_local": price,
                "ccy":         ccy,
                "commission":  comm,
                "fx_rate":     1.0 if ccy == "USD" else 0,
                "gross_usd":   round(qty * price, 2) if ccy == "USD" else 0,
                "notes":       row.get("Notes/Codes", ""),
            })

    return trades
